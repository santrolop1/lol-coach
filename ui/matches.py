"""
ui/matches.py — Página de descarga y listado de partidas.

Permite al usuario:
- Descargar las últimas N partidas desde Riot API.
- Ver la tabla de partidas con filtros de rol y campeón.
- Ver un resumen rápido de estadísticas.
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

import db
from riot_api import RiotClient, RiotAPIError
from parser import parse_match


def render() -> None:
    st.title("🎮 Partidas")

    # ----------------------------------------------------------------
    # Verificar configuración
    # ----------------------------------------------------------------
    puuid    = db.get_config("puuid")
    api_key  = db.get_config("api_key")
    platform = db.get_config("platform") or "la1"

    if not puuid or not api_key:
        st.warning("⚠️ Primero configura tu cuenta en la página **Configuración**.")
        return

    player = db.get_player(puuid)
    if player:
        st.caption(
            f"Jugador: **{player['riot_id']}#{player['tag']}** · "
            f"Nivel {player.get('level', '?')} · {player.get('rank', 'Sin rango')}"
        )

    # ----------------------------------------------------------------
    # Descarga de partidas
    # ----------------------------------------------------------------
    st.subheader("⬇️ Descargar partidas")

    col1, col2 = st.columns([2, 1])
    with col1:
        count = st.slider("Número de partidas a descargar", min_value=5, max_value=50, value=20, step=5)
    with col2:
        queue_options = {
            "Ranked Solo/Duo": 420,
            "Ranked Flex":     440,
            "Normal Draft":    400,
            "Todas":           0,
        }
        queue_label = st.selectbox("Tipo de partida", list(queue_options.keys()))

    if st.button("🔄 Descargar partidas", use_container_width=True, type="primary"):
        _download_matches(puuid, api_key, platform, count, queue_options[queue_label])

    # ----------------------------------------------------------------
    # Tabla de partidas
    # ----------------------------------------------------------------
    st.divider()
    st.subheader("📋 Mis partidas")

    col1, col2 = st.columns(2)
    with col1:
        role_filter = st.selectbox("Filtrar por rol", ["Todos", "ADC", "TOP"])
    with col2:
        role_arg = None if role_filter == "Todos" else role_filter
        all_matches = db.get_matches(puuid, role=role_arg, limit=100)
        champions = sorted({m["champion"] for m in all_matches if m["champion"]})
        champ_filter = st.selectbox("Filtrar por campeón", ["Todos"] + champions)

    matches = all_matches
    if champ_filter != "Todos":
        matches = [m for m in matches if m["champion"] == champ_filter]

    if not matches:
        st.info("No hay partidas guardadas. Descarga algunas con el botón de arriba.")
        return

    # Métricas rápidas
    wins   = sum(1 for m in matches if m["result"] == "WIN")
    losses = len(matches) - wins
    wr     = round(wins / len(matches) * 100, 1) if matches else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Partidas", len(matches))
    c2.metric("Victorias", wins)
    c3.metric("Derrotas", losses)
    c4.metric("Winrate", f"{wr}%")

    # Tabla
    rows = []
    for m in matches:
        duration_min = m["duration_sec"] // 60
        duration_sec = m["duration_sec"] % 60
        kda = f"{m['kills']}/{m['deaths']}/{m['assists']}"
        cs_pm = round(m["cs"] / max(m["duration_sec"] / 60, 1), 1)

        rows.append({
            "Resultado":  "✅ Victoria" if m["result"] == "WIN" else "❌ Derrota",
            "Campeón":    m["champion"],
            "Rol":        m["role"],
            "KDA":        kda,
            "CS":         m["cs"],
            "CS/min":     cs_pm,
            "Daño":       f"{m['damage']:,}",
            "Duración":   f"{duration_min}m {duration_sec:02d}s",
            "Fecha":      (m["played_at"] or "")[:10],
        })

    st.dataframe(rows, use_container_width=True, hide_index=True)


def _download_matches(puuid: str, api_key: str, platform: str, count: int, queue: int) -> None:
    """Descarga partidas de Riot API, parsea y guarda en DB."""
    client = RiotClient(api_key, platform)

    with st.spinner("Obteniendo IDs de partidas..."):
        try:
            match_ids = client.get_match_ids(puuid, count=count, queue=queue)
        except RiotAPIError as e:
            st.error(f"Error obteniendo partidas: {e}")
            return

    if not match_ids:
        st.info("No se encontraron partidas para esta cuenta con el tipo de cola seleccionado.")
        return

    new_ids = [mid for mid in match_ids if not db.match_exists(mid)]

    if not new_ids:
        st.info("✅ Ya tienes las partidas más recientes guardadas.")
        return

    progress = st.progress(0, text="Descargando partidas...")
    saved = 0
    skipped = 0

    for i, match_id in enumerate(new_ids):
        try:
            match_json = client.get_match(match_id)
            match_data = parse_match(match_json, puuid)

            if match_data is None:
                skipped += 1
            elif match_data.role == "OTHER":
                # Guardar igual para no volver a descargar, pero rol filtrado en análisis
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

        progress.progress((i + 1) / len(new_ids), text=f"Descargando {i+1}/{len(new_ids)}...")

    progress.empty()
    st.success(f"✅ {saved} partidas nuevas guardadas · {skipped} omitidas (rol no ADC/TOP o ya existentes).")
    st.rerun()
