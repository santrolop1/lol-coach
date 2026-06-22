"""
main.py — Entry point de LoL Coach.

Uso:
    streamlit run main.py
"""

import sys
from pathlib import Path

# Asegura que los módulos del proyecto sean encontrables
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import streamlit as st

import db
import ui.config   as page_config
import ui.matches  as page_matches
import ui.analysis as page_analysis


def main() -> None:
    st.set_page_config(
        page_title="LoL Coach",
        page_icon="🎮",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Inicializar DB en cada arranque (no-op si ya existe)
    try:
        db.init_db()
    except Exception as e:
        st.error(f"No se pudo inicializar la base de datos en {db.DB_PATH}: {e}")
        st.stop()

    # ----------------------------------------------------------------
    # Sidebar de navegación
    # ----------------------------------------------------------------
    with st.sidebar:
        st.markdown("# 🎮 LoL Coach")
        st.markdown("Análisis personal de ADC y TOP")
        st.divider()

        page = st.radio(
            "Navegación",
            options=["⚙️ Configuración", "🎮 Partidas", "📊 Análisis"],
            label_visibility="collapsed",
        )

        st.divider()

        # Mini estado de configuración
        api_key  = db.get_config("api_key")
        puuid    = db.get_config("puuid")
        if api_key and puuid:
            player = db.get_player(puuid)
            if player:
                st.caption(
                    f"**{player['riot_id']}#{player['tag']}**  \n"
                    f"{player.get('rank', 'Sin rango')} · {player.get('lp', 0)} LP"
                )
        else:
            st.caption("⚠️ Cuenta no configurada")

    # ----------------------------------------------------------------
    # Renderizar página seleccionada
    # ----------------------------------------------------------------
    if page == "⚙️ Configuración":
        page_config.render()
    elif page == "🎮 Partidas":
        page_matches.render()
    elif page == "📊 Análisis":
        page_analysis.render()


if __name__ == "__main__":
    main()
