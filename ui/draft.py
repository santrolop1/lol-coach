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

import sys
import time
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

import analytics
import db
import scorer_v2
import lcu.client as lcu_client
from lcu.champ_select import parse_session, PHASE_LABELS, GAMEFLOW_LABELS
from lcu.models import ChampSelectSession, ChampionSlot, POSITION_DISPLAY
from backend.services.champion_analyzer import analyze_champion_pool, ChampionPoolAnalysis
from backend.services.draft_advisor import (
    analyze_draft, DraftAdvice, DraftScore, DraftRecommendation, DraftWarning,
)

# Mapeo: posición LCU (lowercase) → rol en scorer_v2 / db
_LCU_TO_ROLE: dict[str, str] = {
    "bottom":  "ADC",
    "top":     "TOP",
    "middle":  "MID",
    "jungle":  "JGL",
    "utility": "SUP",
}

# Solo estos roles tienen datos en scorer_v2 (versión actual)
_SUPPORTED_ROLES: set[str] = set(scorer_v2.SUPPORTED_ROLES)


# ── Helpers de datos ─────────────────────────────────────────────────────────

def _find_role_matches(lcu_puuid: str | None, role: str) -> list[dict]:
    """
    Busca partidas para el rol dado tolerando discrepancias de puuid entre
    el LCU y la configuración local (ej. tras reinstalar el cliente).
    Orden: puuid del LCU → puuid de config.

    NO cae a "cualquier puuid con partidas de este rol" — en una máquina
    compartida o tras cambiar de cuenta, eso podía mostrar el pool de
    campeones de otra persona como si fuera el del usuario actual.
    """
    for puuid in filter(None, [
        lcu_puuid,
        db.get_config("puuid"),
    ]):
        matches = db.get_matches(puuid, role=role, limit=200)
        if matches:
            return matches
    return []


def _get_cpa(creds, lcu_role: str) -> ChampionPoolAnalysis | None:
    """
    Carga y cachea ChampionPoolAnalysis para el rol detectado.
    Cache key: rol + (puerto, password) para invalidar en reinicios del cliente.
    Solo soporta los roles de scorer_v2.SUPPORTED_ROLES (ADC, TOP, MID).
    """
    role = _LCU_TO_ROLE.get(lcu_role, "")
    if role not in _SUPPORTED_ROLES:
        return None

    cache_key = f"cpa_{role}_{creds.port}_{creds.password}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    summoner  = lcu_client.get_current_summoner(creds)
    lcu_puuid = summoner.get("puuid") if summoner else None

    matches = _find_role_matches(lcu_puuid, role)
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
    phase_color = "#22C55E" if phase == "ChampSelect" else ("#F59E0B" if phase in ("Lobby", "Matchmaking", "ReadyCheck") else "#374151")
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
            f'<span style="color:#4B5563"><b style="color:#D1D5DB">Rol:</b> {role_str}</span>'
            f'<span style="color:#4B5563"><b style="color:#D1D5DB">Pick:</b> {champ_str}</span>'
            f'<span style="margin-left:auto;color:#374151">'
            f'Bans: {ally_ban_count + enemy_ban_count}/10'
            f'</span>'
            f'</div>',
            unsafe_allow_html=True,
        )


def _track_draft_intelligence(session: ChampSelectSession, advice: DraftAdvice, role_name: str) -> None:
    """
    Registra (Sprint 2, solo local) qué recomendaciones se mostraron y si el
    pick final del jugador estaba entre ellas. Deduplicado con session_state
    para no repetir el mismo evento en cada rerun de 750ms del polling.
    """
    rec_snapshot = tuple(r.champion for r in advice.recommendations)
    if rec_snapshot and st.session_state.get("_di_last_shown") != rec_snapshot:
        st.session_state["_di_last_shown"] = rec_snapshot
        analytics.track_event(
            "draft_recommendations_shown", screen="Draft",
            payload={"role": role_name, "champions": list(rec_snapshot)},
        )

    pick_alias = session.my_champion_alias
    if pick_alias and not st.session_state.get("_di_pick_logged"):
        st.session_state["_di_pick_logged"] = True
        recommended_aliases = {r.champion for r in advice.recommendations}
        avoid_aliases        = {r.champion for r in advice.avoid}
        was_recommended = pick_alias in recommended_aliases
        analytics.track_event(
            "draft_pick_locked", screen="Draft",
            payload={
                "role": role_name,
                "champion": session.my_champion,
                "was_recommended": was_recommended,
                "was_flagged_trap": pick_alias in avoid_aliases,
                "had_history": advice.current_pick_score.has_data if advice.current_pick_score else False,
            },
        )
        # Se conserva para el prompt de feedback post-partida (Sprint 2).
        st.session_state["_last_draft_pick"] = {
            "champion": session.my_champion,
            "was_recommended": was_recommended,
        }
        st.session_state["_feedback_submitted"] = False


def _render_draft_intelligence(advice: DraftAdvice) -> None:
    """Sección Sprint 8: Draft Intelligence — recomendaciones basadas en historial."""
    role = _LCU_TO_ROLE.get(advice.role, advice.role.upper())
    st.markdown(
        f'<div class="sec-header"><span class="sec-header-title">🧠 &nbsp;DRAFT INTELLIGENCE — {role}</span></div>',
        unsafe_allow_html=True,
    )

    if not advice.pool_has_data:
        st.markdown(
            '<div class="card" style="color:#374151;font-size:0.85rem;padding:1.1rem 1.4rem">'
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
        gc = grade_colors.get(ds.grade, "#374151")

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

    col_recs, col_avoid = st.columns([1.15, 1], gap="medium")

    # ── Recomendados ──────────────────────────────────────────────────────────
    with col_recs:
        st.markdown('<div class="card-label">RECOMENDADO</div>', unsafe_allow_html=True)

        if not advice.recommendations:
            st.markdown(
                '<div style="font-size:0.8rem;color:#374151;padding:0.4rem 0">'
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
                    f'<div style="font-size:0.68rem;color:#374151;padding:0 0.9rem 0.3rem">'
                    f'{rec.reason}</div>',
                    unsafe_allow_html=True,
                )

    # ── Evitar ────────────────────────────────────────────────────────────────
    with col_avoid:
        st.markdown('<div class="card-label">EVITAR</div>', unsafe_allow_html=True)

        if not advice.avoid:
            st.markdown(
                '<div style="font-size:0.8rem;color:#374151;padding:0.4rem 0">'
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


def _render_post_game_feedback() -> None:
    """
    Prompt de feedback (Sprint 2): solo aparece si hubo un pick registrado en
    el último Champ Select y todavía no se envió feedback para esa partida.
    Se guarda únicamente en SQLite local (tabla feedback).
    """
    pick = st.session_state.get("_last_draft_pick")
    if not pick or st.session_state.get("_feedback_submitted"):
        return

    st.markdown(
        '<div class="sec-header"><span class="sec-header-title">💬 &nbsp;TU OPINIÓN</span></div>',
        unsafe_allow_html=True,
    )
    with st.form(key="draft_feedback_form"):
        st.markdown(f"¿La recomendación de Draft Intelligence para **{pick['champion']}** te fue útil?")
        stars = st.slider("Valoración", min_value=1, max_value=5, value=3, key="draft_feedback_stars")
        comment = st.text_input("¿Qué mejorarías? (opcional)", key="draft_feedback_comment")
        submitted = st.form_submit_button("Enviar feedback")
        if submitted:
            db.save_feedback(
                "draft_pick", stars=stars,
                champion=pick["champion"], comment=comment or None,
            )
            st.session_state["_feedback_submitted"] = True
            st.success("¡Gracias! Tu feedback se guardó localmente.")


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

    if phase in ("WaitingForStats", "PreEndOfGame", "EndOfGame"):
        _render_post_game_feedback()


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

    # ── 1. Leer credenciales del lockfile / proceso ───────────────────────────
    creds = lcu_client.read_credentials()

    if creds is None:
        _render_disconnected()
        if st.button("🔄 Reintentar conexión", key="draft_retry"):
            st.rerun()
        return

    # ── 2. Obtener fase del cliente ───────────────────────────────────────────
    phase = lcu_client.get_phase(creds)

    if phase is None:
        # Lockfile existe pero el cliente no responde (crash o inicio lento)
        st.markdown(
            f'<div class="draft-status">'
            f'  <div class="draft-status-dot disconnected"></div>'
            f'  <span class="draft-status-label">Conectando…</span>'
            f'  <span class="draft-status-detail">· Puerto {creds.port}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
        _render_disconnected()
        time.sleep(2.0)
        st.rerun()
        return

    # ── 3. Mostrar estado ─────────────────────────────────────────────────────
    dot = "connected" if phase == "ChampSelect" else "idle"
    _render_status_bar(creds, phase, dot)

    # ── 4. Según fase ─────────────────────────────────────────────────────────
    if phase == "ChampSelect":
        raw_session = lcu_client.get_champ_select_session(creds)

        if raw_session is None:
            st.info("Cargando sesión de champ select…")
        else:
            champ_map = _champion_map(creds)
            session   = parse_session(raw_session, champ_map)
            _render_champ_select(session)

            # ── Draft Intelligence (Sprint 8) ──────────────────────────────
            st.markdown("<div style='height:0.5rem'></div>", unsafe_allow_html=True)
            if session.my_role:
                role_name = _LCU_TO_ROLE.get(session.my_role, session.my_role.upper())
                if role_name not in _SUPPORTED_ROLES:
                    st.markdown(
                        f'<div class="sec-header"><span class="sec-header-title">'
                        f'🧠 &nbsp;DRAFT INTELLIGENCE</span></div>'
                        f'<div class="card" style="color:#374151;font-size:0.85rem;padding:1.1rem">'
                        f'Rol <b>{role_name}</b> no soportado en esta versión (ADC, TOP y MID disponibles).'
                        f'</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    cpa = _get_cpa(creds, session.my_role)
                    if cpa is not None:
                        advice = analyze_draft(session, cpa)
                        _render_draft_intelligence(advice)
                        _track_draft_intelligence(session, advice, role_name)
                    else:
                        st.markdown(
                            f'<div class="sec-header"><span class="sec-header-title">'
                            f'🧠 &nbsp;DRAFT INTELLIGENCE — {role_name}</span></div>'
                            '<div class="card" style="color:#374151;font-size:0.85rem;padding:1.1rem 1.4rem">'
                            'Sin historial para este rol. Descarga partidas en la pestaña '
                            '<b>Partidas</b> para activar las recomendaciones.'
                            '</div>',
                            unsafe_allow_html=True,
                        )
            else:
                st.markdown(
                    '<div class="sec-header"><span class="sec-header-title">🧠 &nbsp;DRAFT INTELLIGENCE</span></div>'
                    '<div style="font-size:0.8rem;color:#374151;padding:0.5rem 0">'
                    'Esperando asignación de rol…</div>',
                    unsafe_allow_html=True,
                )

        # Refresh rápido durante champ select
        time.sleep(0.75)
        st.rerun()

    else:
        # Salimos de Champ Select (o nunca entramos) — resetea los flags de
        # dedup para que la próxima sesión de draft se registre de nuevo.
        st.session_state.pop("_di_last_shown", None)
        st.session_state.pop("_di_pick_logged", None)
        _render_waiting(phase)
        # Refresh lento cuando esperamos que empiece champ select
        time.sleep(2.0)
        st.rerun()
