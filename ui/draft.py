"""
ui/draft.py — Página 🎯 Draft: detección de Champ Select + recomendaciones.

Sprint 7: datos en vivo del LCU (picks, bans, timer).
Sprint 8: Draft Intelligence con recomendaciones basadas en historial personal.

Auto-refresh:
  - Desconectado:      sin refresh (botón manual)
  - Conectado / idle:  cada 2 s
  - ChampSelect:       cada 750 ms
"""

from __future__ import annotations

import sqlite3
import sys
import time
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

import db
import scorer_v2
import lcu.client as lcu_client
from backend.services.match_resolver import resolve_matches
from lcu.champ_select import parse_session, PHASE_LABELS, GAMEFLOW_LABELS
from lcu.models import ChampSelectSession, ChampionSlot, POSITION_DISPLAY
from backend.services.champion_analyzer import analyze_champion_pool, ChampionPoolAnalysis
from backend.services.draft_advisor import (
    analyze_draft, DraftAdvice, DraftScore, DraftRecommendation, DraftWarning,
)
from backend.draft.draft_advisor_v2 import enhance_recommendations, DraftContextResult

# Mapeo: posición LCU (lowercase) → rol en scorer_v2 / db
_LCU_TO_ROLE: dict[str, str] = {
    "bottom":  "ADC",
    "top":     "TOP",
    "middle":  "MID",
    "jungle":  "JGL",
    "utility": "SUP",
}

# Solo estos roles tienen datos en scorer_v2 (versión actual)
_SUPPORTED_ROLES: set[str] = {"ADC", "TOP"}


# ── Helpers de datos ─────────────────────────────────────────────────────────

def _cpa_cache_version(role: str) -> str:
    """Versión del cache: cambia cuando se descargan partidas nuevas del rol."""
    try:
        conn = sqlite3.connect("data/lol_coach.db")
        row  = conn.execute(
            "SELECT COUNT(*), MAX(match_id) FROM match WHERE role = ?", (role,)
        ).fetchone()
        conn.close()
        count, latest = row if row else (0, None)
        return f"{count}_{latest or ''}"
    except Exception:
        return "0_"


def _get_cpa(creds, lcu_role: str) -> ChampionPoolAnalysis | None:
    """
    Carga y cachea ChampionPoolAnalysis para el rol detectado.
    Cache key: rol + (puerto, password) para invalidar en reinicios del cliente.
    Solo soporta ADC y TOP en la versión actual.
    """
    role = _LCU_TO_ROLE.get(lcu_role, "")
    if role not in _SUPPORTED_ROLES:
        return None

    version   = _cpa_cache_version(role)
    cache_key = f"cpa_{role}_{creds.port}_{version}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    summoner  = lcu_client.get_current_summoner(creds)
    lcu_puuid = summoner.get("puuid") if summoner else None

    matches = resolve_matches(role=role, extra_puuid=lcu_puuid)
    if not matches:
        st.session_state[cache_key] = None
        return None

    sr  = scorer_v2.analyze_player(matches, role)
    cpa = analyze_champion_pool(matches, role, sr.match_scores)
    st.session_state[cache_key] = cpa
    return cpa


# ── Helpers de UI ─────────────────────────────────────────────────────────────

def _champion_map(creds) -> dict[int, str]:
    """
    Carga y cachea el mapa {id: name} en session_state.
    La clave incluye puerto y password para invalidar en reinicios del cliente.
    """
    cache_key = f"champ_map_{creds.port}_{creds.password}"
    if cache_key not in st.session_state:
        st.session_state[cache_key] = lcu_client.get_champion_map(creds)
    return st.session_state[cache_key]


def _slot_html(slot: ChampionSlot, side: str) -> str:
    """
    Genera el HTML de una fila de jugador en el draft board.
    side: "ally" | "enemy"
    """
    css_cls    = "draft-slot me" if slot.is_local_player else f"draft-slot {('enemy' if side == 'enemy' else '')}"
    pos_label  = POSITION_DISPLAY.get(slot.assigned_position, "?")
    me_tag     = '<span class="draft-slot-me-tag">YO</span>' if slot.is_local_player else ""

    if slot.has_pick:
        champ_html = f'<span class="draft-slot-champ">{slot.champion_name}</span>'
    else:
        champ_html = '<span class="draft-slot-champ empty">—</span>'

    return (
        f'<div class="{css_cls}">'
        f'  <div class="draft-slot-pos">{pos_label}</div>'
        f'  {champ_html}'
        f'  {me_tag}'
        f'</div>'
    )


def _bans_html(ban_names: list[str], label: str) -> str:
    if not ban_names:
        chips = '<span class="draft-no-bans">Sin bans todavía</span>'
    else:
        chips = "".join(f'<span class="draft-ban-chip">{b}</span>' for b in ban_names)
    return (
        f'<div class="draft-team-header">{label}</div>'
        f'<div class="draft-bans">{chips}</div>'
    )


# ── Sub-renders ───────────────────────────────────────────────────────────────

def _render_status_bar(creds, phase: str, dot_class: str = "connected") -> None:
    phase_label = GAMEFLOW_LABELS.get(phase, phase)
    phase_color = "#22C55E" if phase == "ChampSelect" else ("#F59E0B" if phase in ("Lobby", "Matchmaking", "ReadyCheck") else "#6B7280")
    st.markdown(
        f'<div class="draft-status">'
        f'  <div class="draft-status-dot {dot_class}"></div>'
        f'  <span class="draft-status-label">Cliente conectado</span>'
        f'  <span class="draft-status-detail">· Puerto {creds.port} · PID {creds.pid}</span>'
        f'  <span class="draft-status-phase" style="color:{phase_color}">{phase_label}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_timer(session: ChampSelectSession) -> None:
    timer      = session.timer
    secs       = timer.time_left_sec
    phase_name = PHASE_LABELS.get(timer.phase, timer.phase)
    urgent_cls = "urgent" if secs <= 8 and not timer.is_infinite else ""
    secs_str   = "∞" if timer.is_infinite else f"{int(secs)}s"

    st.markdown(
        f'<div class="draft-timer-bar">'
        f'  <div class="draft-timer-phase">{phase_name}</div>'
        f'  <div class="draft-timer-sec {urgent_cls}">{secs_str}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
    if not timer.is_infinite and timer.total_time_ms > 0:
        st.progress(timer.progress_pct)


def _render_champ_select(session: ChampSelectSession) -> None:
    _render_timer(session)

    col_ally, col_enemy = st.columns(2, gap="large")

    with col_ally:
        st.markdown('<div class="draft-team-header">MI EQUIPO</div>', unsafe_allow_html=True)
        for slot in session.my_team:
            st.markdown(_slot_html(slot, "ally"), unsafe_allow_html=True)
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        st.markdown(_bans_html(session.bans.my_team_bans, "BANS ALIADOS"), unsafe_allow_html=True)

    with col_enemy:
        st.markdown('<div class="draft-team-header">EQUIPO ENEMIGO</div>', unsafe_allow_html=True)
        for slot in session.their_team:
            st.markdown(_slot_html(slot, "enemy"), unsafe_allow_html=True)
        st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
        st.markdown(_bans_html(session.bans.their_team_bans, "BANS ENEMIGOS"), unsafe_allow_html=True)

    # Resumen: mi situación actual
    me = session.me
    if me:
        role_str  = POSITION_DISPLAY.get(me.assigned_position, "?")
        champ_str = me.champion_name if me.has_pick else "Sin seleccionar"
        ally_ban_count  = len(session.bans.my_team_bans)
        enemy_ban_count = len(session.bans.their_team_bans)

        st.markdown(
            f'<div class="info-bar" style="margin-top:1.25rem">'
            f'<span style="color:#8B5CF6">👤</span>'
            f'<span style="color:#9CA3AF"><b style="color:#D1D5DB">Rol:</b> {role_str}</span>'
            f'<span style="color:#9CA3AF"><b style="color:#D1D5DB">Pick:</b> {champ_str}</span>'
            f'<span style="margin-left:auto;color:#6B7280">'
            f'Bans: {ally_ban_count + enemy_ban_count}/10'
            f'</span>'
            f'</div>',
            unsafe_allow_html=True,
        )


def _render_draft_intelligence(advice: DraftAdvice, session: ChampSelectSession) -> None:
    """Sección Sprint 8+9: Draft Intelligence — historial + análisis contextual."""
    role = _LCU_TO_ROLE.get(advice.role, advice.role.upper())
    st.markdown(
        f'<div class="sec-header"><span class="sec-header-title">🧠 &nbsp;DRAFT INTELLIGENCE — {role}</span></div>',
        unsafe_allow_html=True,
    )

    if not advice.pool_has_data:
        st.markdown(
            '<div class="card" style="color:#6B7280;font-size:0.85rem;padding:1.1rem 1.4rem">'
            'Sin historial para este rol. Descarga partidas en la pestaña '
            '<b>Partidas</b> para activar las recomendaciones.'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Draft Score del pick actual ───────────────────────────────────────────
    ds = advice.current_pick_score
    if ds is not None:
        grade_colors = {"A": "#22C55E", "B": "#8B5CF6", "C": "#3B82F6", "D": "#F59E0B", "F": "#EF4444"}
        gc = grade_colors.get(ds.grade, "#6B7280")

        if ds.has_data:
            factors = [
                ("Familiaridad",  ds.familiarity_pts, 30.0, "#8B5CF6"),
                ("Rendimiento",   ds.performance_pts, 30.0, "#3B82F6"),
                ("Consistencia",  ds.consistency_pts, 25.0, "#22C55E"),
                ("WR personal",   ds.winrate_pts,     15.0, "#F59E0B"),
            ]
            bars_html = ""
            for label, pts, max_pts, color in factors:
                pct = pts / max_pts * 100
                bars_html += (
                    f'<div class="di-factor-row">'
                    f'  <div class="di-factor-label">{label}</div>'
                    f'  <div class="di-factor-bar-wrap">'
                    f'    <div class="di-factor-bar-fill" style="width:{pct:.0f}%;background:{color}"></div>'
                    f'  </div>'
                    f'  <div class="di-factor-pts">{pts:.0f}/{max_pts:.0f}</div>'
                    f'</div>'
                )
            score_content = (
                f'<div class="di-score-header">'
                f'  <span class="di-score-champion">{ds.champion}</span>'
                f'  <span class="di-score-grade" style="color:{gc}">{ds.grade}</span>'
                f'  <span class="di-score-total">{ds.total:.0f}/100 · {ds.grade_label}</span>'
                f'</div>'
                + bars_html
            )
        else:
            score_content = (
                f'<div class="di-score-header">'
                f'  <span class="di-score-champion">{ds.champion}</span>'
                f'  <span class="di-score-grade" style="color:{gc}">F</span>'
                f'  <span class="di-score-total">Sin historial — 0 partidas registradas</span>'
                f'</div>'
            )

        st.markdown(
            f'<div class="di-score-card">'
            f'  <div class="di-score-label">DRAFT SCORE — PICK ACTUAL</div>'
            + score_content
            + '</div>',
            unsafe_allow_html=True,
        )

    # ── Contexto v2: enriquecer recomendaciones con sinergia y amenaza ──────
    ally_names  = [s.champion_name for s in session.my_team    if s.has_pick and not s.is_local_player]
    enemy_names = [s.champion_name for s in session.their_team if s.has_pick]
    ctx_result: DraftContextResult | None = None
    if advice.recommendations:
        ctx_result = enhance_recommendations(advice.recommendations, ally_names, enemy_names)

    col_recs, col_avoid = st.columns([1.15, 1], gap="medium")

    # ── Recomendados ──────────────────────────────────────────────────────────
    with col_recs:
        st.markdown('<div class="card-label">RECOMENDADO</div>', unsafe_allow_html=True)

        if not advice.recommendations:
            st.markdown(
                '<div style="font-size:0.8rem;color:#6B7280;padding:0.4rem 0">'
                'Sin recomendaciones disponibles (todos los picks baneados o sin datos).'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            rank_icons = {1: "🥇", 2: "🥈", 3: "🥉"}
            for rec in advice.recommendations:
                icon     = rank_icons.get(rec.rank, str(rec.rank))
                conf_pct = int(rec.confidence)
                wr_color = "#22C55E" if rec.winrate >= 0.55 else ("#F59E0B" if rec.winrate >= 0.45 else "#EF4444")

                # Intentar obtener contexto v2
                ctx = ctx_result.scores.get(rec.champion.lower()) if ctx_result else None

                if ctx and ctx.context_available:
                    sy_color = "#22C55E" if ctx.synergy >= 12 else ("#F59E0B" if ctx.synergy >= 6 else "#6B7280")
                    th_color = "#EF4444" if ctx.threat <= -10 else ("#F59E0B" if ctx.threat <= -5 else "#6B7280")
                    sy_str   = f"+{ctx.synergy:.0f}"
                    th_str   = f"{ctx.threat:.0f}"
                    # Razones positivas (historial + sinergia)
                    pos_reasons = ctx.pos_reasons[:]
                    if not pos_reasons:
                        pos_reasons = [rec.reason] if rec.reason else []
                    neg_reasons = ctx.neg_reasons

                    reasons_html = ""
                    for r in pos_reasons[:2]:
                        reasons_html += f'<span class="di-reason-pos">✓ {r}</span>'
                    for r in neg_reasons[:1]:
                        reasons_html += f'<span class="di-reason-neg">⚠ {r}</span>'

                    st.markdown(
                        f'<div class="di-rec-v2">'
                        f'  <div class="di-v2-header">'
                        f'    <div class="di-v2-rank">{icon}</div>'
                        f'    <div class="di-v2-champ">{rec.champion}</div>'
                        f'    <span class="di-rec-tag {rec.classification}">{rec.classification}</span>'
                        f'  </div>'
                        f'  <div class="di-v2-scores">'
                        f'    <div class="di-v2-main">'
                        f'      <span class="di-v2-ds">{ctx.draft_score_v2:.0f}</span>'
                        f'      <span class="di-v2-ds-lbl">Draft Score</span>'
                        f'    </div>'
                        f'    <div class="di-v2-breakdown">'
                        f'      <div class="di-v2-row">'
                        f'        <span class="di-v2-lbl">Pick Value</span>'
                        f'        <span class="di-v2-val" style="color:#D1D5DB">{ctx.pick_value:.0f}</span>'
                        f'      </div>'
                        f'      <div class="di-v2-row">'
                        f'        <span class="di-v2-lbl">Sinergia</span>'
                        f'        <span class="di-v2-val" style="color:{sy_color}">{sy_str}</span>'
                        f'      </div>'
                        f'      <div class="di-v2-row">'
                        f'        <span class="di-v2-lbl">Amenaza</span>'
                        f'        <span class="di-v2-val" style="color:{th_color}">{th_str}</span>'
                        f'      </div>'
                        f'      <div class="di-v2-row">'
                        f'        <span class="di-v2-lbl">WR</span>'
                        f'        <span class="di-v2-val" style="color:{wr_color}">{rec.winrate:.0%}</span>'
                        f'      </div>'
                        f'    </div>'
                        f'  </div>'
                        f'  <div class="di-v2-reasons">{reasons_html}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    # Fallback: formato clásico para campeones sin perfil
                    st.markdown(
                        f'<div class="di-rec-row">'
                        f'  <div class="di-rec-rank">{icon}</div>'
                        f'  <div class="di-rec-champ">{rec.champion}</div>'
                        f'  <div class="di-rec-stats">'
                        f'    <span style="color:{wr_color};font-weight:700">{rec.winrate:.0%}</span>'
                        f'    &nbsp;·&nbsp; Score {rec.avg_score:.0f}'
                        f'    &nbsp;·&nbsp; {rec.games}P'
                        f'  </div>'
                        f'  <span class="di-rec-tag {rec.classification}">{rec.classification}</span>'
                        f'  <div class="di-rec-conf">⬛ {conf_pct}%</div>'
                        f'</div>'
                        f'<div style="font-size:0.68rem;color:#6B7280;padding:0 0.9rem 0.3rem">'
                        f'{rec.reason}</div>',
                        unsafe_allow_html=True,
                    )

    # ── Evitar ────────────────────────────────────────────────────────────────
    with col_avoid:
        st.markdown('<div class="card-label">EVITAR</div>', unsafe_allow_html=True)

        if not advice.avoid:
            st.markdown(
                '<div style="font-size:0.8rem;color:#6B7280;padding:0.4rem 0">'
                'Sin picks de riesgo detectados en tu historial.'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            for av in advice.avoid:
                st.markdown(
                    f'<div class="di-avoid-row">'
                    f'  <span style="font-size:0.75rem">⛔</span>'
                    f'  <div class="di-avoid-champ">{av.champion}</div>'
                    f'  <div class="di-avoid-stats">{av.reason}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    # ── Advertencias ─────────────────────────────────────────────────────────
    if advice.warnings:
        st.markdown('<div class="card-label" style="margin-top:0.75rem">ALERTAS</div>', unsafe_allow_html=True)
        icons = {"critical": "🚨", "warning": "⚠️", "info": "ℹ️"}
        for w in advice.warnings:
            st.markdown(
                f'<div class="di-warn-row {w.level}">'
                f'  <div class="di-warn-icon">{icons[w.level]}</div>'
                f'  <div class="di-warn-text">{w.text}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


def _render_waiting(phase: str) -> None:
    phase_label = GAMEFLOW_LABELS.get(phase, phase)

    if phase == "InProgress":
        icon  = "🎮"
        title = "Partida en curso"
        body  = "Vuelve aquí cuando termines para ver tu coaching post-partida."
    elif phase in ("WaitingForStats", "PreEndOfGame", "EndOfGame"):
        icon  = "📊"
        title = "Fin de partida"
        body  = "Descarga las partidas en la pestaña Partidas para actualizar tu coaching."
    elif phase == "ReadyCheck":
        icon  = "⚡"
        title = "¡Partida encontrada!"
        body  = "Acepta la partida para entrar a Champ Select."
    elif phase in ("Lobby", "Matchmaking"):
        icon  = "🔍"
        title = "Buscando partida"
        body  = "Cuando entres a Champ Select esta página se actualizará automáticamente."
    else:
        icon  = "🕹️"
        title = "Cliente conectado"
        body  = "Entra a una partida para ver el draft en tiempo real."

    st.markdown(
        f'<div class="draft-waiting">'
        f'  <div class="draft-waiting-icon">{icon}</div>'
        f'  <div class="draft-waiting-title">{title}</div>'
        f'  <div class="draft-waiting-body">{body}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_disconnected() -> None:
    st.markdown(
        '<div class="draft-waiting">'
        '  <div class="draft-waiting-icon">🔌</div>'
        '  <div class="draft-waiting-title">Cliente no detectado</div>'
        '  <div class="draft-waiting-body">'
        '    Abre el cliente de League of Legends e inicia sesión.<br>'
        '    La página se actualizará automáticamente cuando detecte el cliente.'
        '  </div>'
        '</div>',
        unsafe_allow_html=True,
    )


# ── Render principal ──────────────────────────────────────────────────────────

def render() -> None:
    st.title("🎯 Draft")

    # ── Cache de sesión para champion_map y CPA (UI concern) ─────────────────
    # Los caches se pasan al ViewModel para evitar re-fetching en cada ciclo.
    champ_map_cache: dict = st.session_state.get("draft_champ_map", None)
    cpa_cache: dict       = st.session_state.setdefault("draft_cpa_cache", {})

    # ── Construir ViewModel (toda la lógica vive aquí) ────────────────────────
    from backend.viewmodels.draft_vm import build_draft
    vm = build_draft(champion_map_cache=champ_map_cache, cpa_cache=cpa_cache)

    # Persistir el champion_map en session_state si fue cargado esta vez
    if vm.champion_map:
        st.session_state["draft_champ_map"] = vm.champion_map

    # ── Render según estado ───────────────────────────────────────────────────
    if not vm.lcu_connected:
        _render_disconnected()
        if st.button("🔄 Reintentar conexión", key="draft_retry"):
            st.rerun()
        return

    if vm.phase is None:
        # Lockfile existe pero el cliente no responde
        st.markdown(
            f'<div class="draft-status">'
            f'  <div class="draft-status-dot disconnected"></div>'
            f'  <span class="draft-status-label">Conectando…</span>'
            f'  <span class="draft-status-detail">· Puerto {vm.credentials.port}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        _render_disconnected()
        time.sleep(2.0)
        st.rerun()
        return

    dot = "connected" if vm.phase == "ChampSelect" else "idle"
    _render_status_bar(vm.credentials, vm.phase, dot)

    if vm.phase == "ChampSelect":
        if vm.session is None:
            st.info("Cargando sesión de champ select…")
        else:
            _render_champ_select(vm.session)
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)

            if vm.session.my_role:
                if vm.advice is not None:
                    _render_draft_intelligence(vm.advice, vm.session)
                elif not vm.role_supported:
                    role_name = vm.role or vm.session.my_role.upper()
                    st.markdown(
                        f'<div class="sec-header"><span class="sec-header-title">'
                        f'🧠 &nbsp;DRAFT INTELLIGENCE</span></div>'
                        f'<div class="card" style="color:#6B7280;font-size:0.85rem;padding:1.1rem">'
                        f'Rol <b>{role_name}</b> no soportado en esta versión (ADC y TOP disponibles).'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    '<div class="sec-header"><span class="sec-header-title">🧠 &nbsp;DRAFT INTELLIGENCE</span></div>'
                    '<div style="font-size:0.8rem;color:#6B7280;padding:0.5rem 0">'
                    'Esperando asignación de rol…</div>',
                    unsafe_allow_html=True,
                )

        time.sleep(0.75)
        st.rerun()
    else:
        _render_waiting(vm.phase)
        time.sleep(2.0)
        st.rerun()
