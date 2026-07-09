"""
ui/matches.py — Página de descarga y listado de partidas.

Solo renderiza. Toda la lógica de datos viene del MatchesViewModel.
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

import db
from riot_api import RiotClient, RiotAPIError
from parser import parse_match
from backend.viewmodels.matches_vm import build_matches, MatchCard


# ---------------------------------------------------------------------------
# Helpers de presentación (solo render, sin cálculos)
# ---------------------------------------------------------------------------

def _score_color(score: float) -> str:
    if score >= 70:
        return "#22C55E"
    if score >= 40:
        return "#F59E0B"
    return "#EF4444"


def _match_card_html(card: MatchCard) -> str:
    """Genera el HTML de una tarjeta de partida desde un MatchCard pre-calculado."""
    css_cls  = "mc mc-win" if card.is_win else "mc mc-loss"
    res_cls  = "mc-res mc-res-win" if card.is_win else "mc-res mc-res-loss"
    res_text = "VICTORIA" if card.is_win else "DERROTA"
    color    = _score_color(card.overall_score)
    return f"""
<div class="{css_cls}">
    <div class="{res_cls}">{res_text}</div>
    <div class="mc-champ">{card.champion}</div>
    <div class="mc-role">{card.role}</div>
    <div class="mc-kda">{card.kda}</div>
    <div class="mc-score" style="color:{color}">{card.overall_score:.0f}</div>
    <div class="mc-tag mc-pos">✓ {card.best_dim}</div>
    <div class="mc-tag mc-neg">✗ {card.worst_dim}</div>
</div>
"""


# ---------------------------------------------------------------------------
# Render principal
# ---------------------------------------------------------------------------

def render() -> None:
    st.title("🎮 Partidas")

    # ── Filtros (determinan qué construye el ViewModel) ───────────────────────
    col1, col2 = st.columns(2)
    with col1:
        role_filter = st.selectbox("Filtrar por rol", ["Todos", "ADC", "TOP"])

    # Construir ViewModel (toda la lógica de datos vive aquí)
    role_arg = None if role_filter == "Todos" else role_filter
    vm = build_matches(role_filter=role_arg)

    if not vm.has_config:
        st.warning("⚠️ Primero configura tu cuenta en **Configuración**.")
        return

    with col2:
        champ_filter = st.selectbox("Filtrar por campeón", ["Todos"] + vm.available_champs)

    # Reconstruir con filtro de campeón si fue seleccionado
    champ_arg = None if champ_filter == "Todos" else champ_filter
    if champ_arg:
        vm = build_matches(role_filter=role_arg, champion_filter=champ_arg)

    # ── Info del jugador ──────────────────────────────────────────────────────
    if vm.player:
        p = vm.player
        st.caption(
            f"**{p['riot_id']}#{p['tag']}** · "
            f"Nivel {p.get('level', '?')} · {p.get('rank', 'Sin rango')}"
        )

    # ── Últimas 5 partidas — tarjetas ─────────────────────────────────────────
    if vm.recent_cards:
        st.markdown('<div class="sec-label">Últimas 5 partidas</div>', unsafe_allow_html=True)
        cols = st.columns(len(vm.recent_cards))
        for col, card in zip(cols, vm.recent_cards):
            with col:
                st.markdown(_match_card_html(card), unsafe_allow_html=True)

    # ── Descarga de partidas ──────────────────────────────────────────────────
    st.markdown('<div class="sec-label">Descargar partidas</div>', unsafe_allow_html=True)
    col1, col2 = st.columns([2, 1])
    with col1:
        count = st.slider("Número de partidas", min_value=5, max_value=50, value=20, step=5)
    with col2:
        queue_options = {
            "Ranked Solo/Duo": 420,
            "Ranked Flex":     440,
            "Normal Draft":    400,
            "Todas":           0,
        }
        queue_label = st.selectbox("Tipo", list(queue_options.keys()))

    api_key  = db.get_config("api_key")
    platform = db.get_config("platform") or "la1"
    puuid    = db.get_config("puuid")
    if not api_key:
        st.warning("⚠️ No hay API Key configurada. Ve a **Configuración** y actualiza tu clave.")
    else:
        if st.button("🔄 Descargar partidas", use_container_width=True, type="primary"):
            _download_matches(puuid, api_key, platform, count, queue_options[queue_label])

    # ── Tabla de partidas ─────────────────────────────────────────────────────
    st.markdown('<div class="sec-label">Historial completo</div>', unsafe_allow_html=True)

    if not vm.table_rows:
        st.info("No hay partidas guardadas todavía. Usa el botón de arriba para descargar partidas.")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Partidas", vm.summary.total)
    c2.metric("Victorias", vm.summary.wins)
    c3.metric("Derrotas",  vm.summary.losses)
    c4.metric("Winrate",   f"{vm.summary.winrate}%")

    rows = [
        {
            "Resultado": r.result,
            "Campeón":   r.champion,
            "Rol":       r.role,
            "KDA":       r.kda,
            "CS":        r.cs,
            "CS/min":    r.cs_pm,
            "Daño":      r.damage,
            "Duración":  r.duration,
            "Fecha":     r.date,
        }
        for r in vm.table_rows
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)

    # ── Análisis V2 ───────────────────────────────────────────────────────────
    if vm.v2_analysis and vm.v2_analysis.available:
        v2 = vm.v2_analysis
        with st.expander(f"📊 Análisis detallado V2 — {v2.role} ({len(v2.detail_rows)} partidas)"):
            detail_rows = [
                {
                    "Fecha":     r.date,
                    "Campeón":   r.champion,
                    "Resultado": r.result,
                    "Overall":   r.overall,
                    "KDA":       r.kda,
                    **r.dimensions,
                }
                for r in v2.detail_rows
            ]
            st.dataframe(detail_rows, use_container_width=True, hide_index=True)

            avg_parts = [f"Overall: **{v2.avg_overall:.1f}**"]
            for name, score in v2.avg_dims.items():
                avg_parts.append(f"{name}: **{score:.1f}**")
            st.caption("Promedios V2 — " + " · ".join(avg_parts))


# ---------------------------------------------------------------------------
# Descarga
# ---------------------------------------------------------------------------

def _download_matches(
    puuid: str, api_key: str, platform: str, count: int, queue: int
) -> None:
    client = RiotClient(api_key, platform)

    with st.spinner("Obteniendo IDs de partidas..."):
        try:
            match_ids = client.get_match_ids(puuid, count=count, queue=queue)
        except RiotAPIError as e:
            st.error(f"Error obteniendo partidas: {e}")
            return

    if not match_ids:
        st.info("No se encontraron partidas con el tipo de cola seleccionado.")
        return

    new_ids = [mid for mid in match_ids if not db.match_exists(mid)]

    if not new_ids:
        st.info("✅ Ya tienes las partidas más recientes guardadas.")
        return

    progress = st.progress(0, text="Descargando partidas...")
    saved = skipped = 0

    for i, match_id in enumerate(new_ids):
        try:
            match_json = client.get_match(match_id)
            match_data = parse_match(match_json, puuid)

            if match_data is None:
                skipped += 1
            elif match_data.role == "OTHER":
                db.save_match(match_data.to_dict())
                skipped += 1
            else:
                db.save_match(match_data.to_dict())
                saved += 1

        except RiotAPIError as e:
            st.warning(f"No se pudo descargar {match_id}: {e}")
            skipped += 1
        except (KeyError, ValueError):
            st.warning(f"Partida {match_id}: formato inesperado, omitida.")
            skipped += 1

        progress.progress(
            (i + 1) / len(new_ids),
            text=f"Descargando {i + 1}/{len(new_ids)}...",
        )

    progress.empty()
    if saved > 0:
        from backend.services import sync_service
        sync_service.invalidate_caches(st.session_state)
    st.success(
        f"✅ {saved} partidas nuevas guardadas · "
        f"{skipped} omitidas (rol no ADC/TOP o ya existentes)."
    )
    st.rerun()
