"""
ui/matches.py — Página de descarga y listado de partidas.
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

import db
import scorer_v2
from riot_api import RiotClient, RiotAPIError
from parser import parse_match
from scorer import calculate_score


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _score_color(score: float) -> str:
    if score >= 70:
        return "#22C55E"
    if score >= 40:
        return "#F59E0B"
    return "#EF4444"


def _match_card_html(m: dict) -> str:
    """Genera el HTML de una tarjeta de partida individual."""
    is_win    = m["result"] == "WIN"
    css_cls   = "mc mc-win" if is_win else "mc mc-loss"
    res_cls   = "mc-res mc-res-win" if is_win else "mc-res mc-res-loss"
    res_text  = "VICTORIA" if is_win else "DERROTA"

    kda = f"{m['kills']}/{m['deaths']}/{m['assists']}"

    sc    = calculate_score(m)
    score = sc.overall_score
    color = _score_color(score)

    dims = {
        "Farm":  sc.farm_score,
        "Superv": sc.survival_score,
        "Pelea":  sc.fight_score,
    }
    best  = max(dims, key=dims.get)
    worst = min(dims, key=dims.get)

    return f"""
<div class="{css_cls}">
    <div class="{res_cls}">{res_text}</div>
    <div class="mc-champ">{m['champion']}</div>
    <div class="mc-role">{m['role']}</div>
    <div class="mc-kda">{kda}</div>
    <div class="mc-score" style="color:{color}">{score:.0f}</div>
    <div class="mc-tag mc-pos">✓ {best}</div>
    <div class="mc-tag mc-neg">✗ {worst}</div>
</div>
"""


# ---------------------------------------------------------------------------
# Render principal
# ---------------------------------------------------------------------------

def render() -> None:
    st.title("🎮 Partidas")

    # ----------------------------------------------------------------
    # Verificar configuración
    # ----------------------------------------------------------------
    puuid    = db.get_config("puuid")
    platform = db.get_config("platform") or "la1"

    if not puuid:
        st.warning("⚠️ Primero configura tu cuenta en **Configuración**.")
        return

    player = db.get_player(puuid)
    if player:
        st.caption(
            f"**{player['riot_id']}#{player['tag']}** · "
            f"Nivel {player.get('level', '?')} · {player.get('rank', 'Sin rango')}"
        )

    # ----------------------------------------------------------------
    # Últimas 5 partidas — tarjetas visuales
    # ----------------------------------------------------------------
    all_role_matches = db.get_matches(puuid, limit=100)
    adc_top = [m for m in all_role_matches if m["role"] in ("ADC", "TOP")]
    last_5  = adc_top[:5]

    if last_5:
        st.markdown('<div class="sec-label">Últimas 5 partidas</div>',
                    unsafe_allow_html=True)
        cols = st.columns(len(last_5))
        for col, m in zip(cols, last_5):
            with col:
                st.markdown(_match_card_html(m), unsafe_allow_html=True)

    # ----------------------------------------------------------------
    # Descarga de partidas
    # ----------------------------------------------------------------
    st.markdown('<div class="sec-label">Descargar partidas</div>',
                unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])
    with col1:
        count = st.slider(
            "Número de partidas",
            min_value=5, max_value=50, value=20, step=5,
        )
    with col2:
        queue_options = {
            "Ranked Solo/Duo": 420,
            "Ranked Flex":     440,
            "Normal Draft":    400,
            "Todas":           0,
        }
        queue_label = st.selectbox("Tipo", list(queue_options.keys()))

    api_key = db.get_config("api_key")
    if not api_key:
        st.warning(
            "⚠️ No hay API Key configurada. "
            "Para descargar partidas nuevas, ve a **Configuración** y actualiza tu clave."
        )
    else:
        if st.button("🔄 Descargar partidas", use_container_width=True, type="primary"):
            _download_matches(puuid, api_key, platform, count, queue_options[queue_label])

    # ----------------------------------------------------------------
    # Tabla de partidas
    # ----------------------------------------------------------------
    st.markdown('<div class="sec-label">Historial completo</div>',
                unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        role_filter = st.selectbox("Filtrar por rol", ["Todos", "ADC", "TOP"])
    with col2:
        role_arg   = None if role_filter == "Todos" else role_filter
        all_matches = db.get_matches(puuid, role=role_arg, limit=100)
        champions   = sorted({m["champion"] for m in all_matches if m["champion"]})
        champ_filter = st.selectbox("Filtrar por campeón", ["Todos"] + champions)

    matches = all_matches
    if champ_filter != "Todos":
        matches = [m for m in matches if m["champion"] == champ_filter]

    if not matches:
        st.info(
            "No hay partidas guardadas todavía. "
            "Usa el botón de arriba para descargar partidas."
        )
        return

    # Resumen
    wins   = sum(1 for m in matches if m["result"] == "WIN")
    losses = len(matches) - wins
    wr     = round(wins / len(matches) * 100, 1) if matches else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Partidas", len(matches))
    c2.metric("Victorias", wins)
    c3.metric("Derrotas", losses)
    c4.metric("Winrate", f"{wr}%")

    # Tabla
    rows = []
    for m in matches:
        dur_min = m["duration_sec"] // 60
        dur_sec = m["duration_sec"] % 60
        cs_pm   = round(m["cs"] / max(m["duration_sec"] / 60, 1), 1)
        rows.append({
            "Resultado": "✅ Victoria" if m["result"] == "WIN" else "❌ Derrota",
            "Campeón":   m["champion"],
            "Rol":       m["role"],
            "KDA":       f"{m['kills']}/{m['deaths']}/{m['assists']}",
            "CS":        m["cs"],
            "CS/min":    cs_pm,
            "Daño":      f"{m['damage']:,}",
            "Duración":  f"{dur_min}m {dur_sec:02d}s",
            "Fecha":     (m["played_at"] or "")[:10],
        })

    st.dataframe(rows, use_container_width=True, hide_index=True)  # noqa: kept width

    # ----------------------------------------------------------------
    # Análisis detallado V2 (solo cuando hay un rol concreto)
    # ----------------------------------------------------------------
    if role_filter in ("ADC", "TOP"):
        role_matches_v2 = [m for m in matches if m["role"] == role_filter]
        if len(role_matches_v2) >= 5:
            with st.expander(f"📊 Análisis detallado V2 — {role_filter} ({len(role_matches_v2)} partidas)"):
                sr = scorer_v2.analyze_player(role_matches_v2, role_filter)

                # Nombres de dimensiones según rol
                dim_names = [d.name for d in sr.match_scores[0].dimensions] if sr.match_scores else []

                # Tabla por partida
                detail_rows = []
                for m, ms in zip(role_matches_v2, sr.match_scores):
                    row = {
                        "Fecha":     (m.get("played_at") or "")[:10],
                        "Campeón":   m.get("champion", "?"),
                        "Resultado": "✅" if m.get("result") == "WIN" else "❌",
                        "Overall":   round(ms.overall_score, 1) if ms.overall_score else 0,
                        "KDA":       f"{m.get('kills',0)}/{m.get('deaths',0)}/{m.get('assists',0)}",
                    }
                    for d in ms.dimensions:
                        row[d.name] = round(d.score, 1)
                    detail_rows.append(row)

                st.dataframe(detail_rows, use_container_width=True, hide_index=True)

                # Promedios de dimensiones
                avg_overall = sr.overall_score
                avg_dims = sr.dimensions  # dict: {name: score}

                avg_parts = [f"Overall: **{avg_overall:.1f}**"]
                for name, score in avg_dims.items():
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
    st.success(
        f"✅ {saved} partidas nuevas guardadas · "
        f"{skipped} omitidas (rol no ADC/TOP o ya existentes)."
    )
    st.rerun()
