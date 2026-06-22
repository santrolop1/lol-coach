"""
main.py — Entry point de LoL Coach.

Uso:
    streamlit run main.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import streamlit as st

import db
import ui.config   as page_config
import ui.matches  as page_matches
import ui.analysis as page_analysis

# ---------------------------------------------------------------------------
# CSS global
# ---------------------------------------------------------------------------

_CSS = """
<style>
/* ── Score Hero ─────────────────────────────────── */
.score-hero {
    text-align: center;
    padding: 2.5rem 1rem 2rem;
    border-radius: 14px;
    border: 1px solid rgba(128,128,128,0.15);
    background: var(--secondary-background-color);
    margin-bottom: 1.5rem;
}
.score-value {
    font-size: 5.5rem;
    font-weight: 800;
    letter-spacing: -4px;
    line-height: 1;
}
.score-denom {
    font-size: 2rem;
    font-weight: 300;
    color: #64748B;
    letter-spacing: 0;
}
.score-label {
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    margin-top: 0.85rem;
}

/* ── Section divider ────────────────────────────── */
.sec-label {
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: #64748B;
    margin: 2rem 0 0.85rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid rgba(128,128,128,0.14);
}

/* ── Veredicto ──────────────────────────────────── */
.veredicto {
    padding: 1.2rem 1.5rem;
    border-radius: 10px;
    border: 1px solid rgba(128,128,128,0.13);
    background: var(--secondary-background-color);
    font-size: 1rem;
    line-height: 1.8;
    margin-bottom: 0.5rem;
}

/* ── Objective card ─────────────────────────────── */
.obj-card {
    border-radius: 10px;
    padding: 1.4rem 1.6rem;
    border: 1px solid rgba(59,130,246,0.3);
    border-left: 3px solid #3B82F6;
    background: rgba(59,130,246,0.07);
    margin-bottom: 1rem;
}
.obj-card .oc-label {
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #3B82F6;
    margin-bottom: 0.45rem;
}
.obj-card .oc-goal {
    font-size: 1.15rem;
    font-weight: 700;
    line-height: 1.3;
    margin-bottom: 0.45rem;
}
.obj-card .oc-action {
    font-size: 0.88rem;
    color: #94A3B8;
    line-height: 1.65;
}

/* ── Coach cards (fortalezas / debilidades) ─────── */
.coach-card {
    border-radius: 10px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 0.75rem;
    border: 1px solid rgba(128,128,128,0.12);
    background: var(--secondary-background-color);
}
.coach-card .cc-label {
    font-size: 0.62rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #64748B;
    margin-bottom: 0.35rem;
}
.coach-card .cc-stat {
    font-size: 1.45rem;
    font-weight: 700;
    line-height: 1.1;
    margin-bottom: 0.25rem;
}
.coach-card .cc-body {
    font-size: 0.86rem;
    color: #94A3B8;
    line-height: 1.6;
}
.coach-card .cc-row {
    margin-top: 0.5rem;
    font-size: 0.82rem;
    line-height: 1.55;
}
.coach-card .cc-cause  { color: #94A3B8; font-style: italic; }
.coach-card .cc-action { color: #CBD5E1; }
.strength-card { border-left: 3px solid #F59E0B; }
.weakness-card  { border-left: 3px solid #EF4444; }

/* ── Match cards (últimas 5) ────────────────────── */
.mc {
    border-radius: 10px;
    padding: 1rem 0.75rem 0.85rem;
    text-align: center;
    border: 1px solid rgba(128,128,128,0.12);
    background: var(--secondary-background-color);
    height: 100%;
}
.mc-win  { border-top: 3px solid #22C55E; }
.mc-loss { border-top: 3px solid #EF4444; }
.mc-res  { font-size: 0.62rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; }
.mc-res-win  { color: #22C55E; }
.mc-res-loss { color: #EF4444; }
.mc-champ { font-size: 0.95rem; font-weight: 700; margin: 0.35rem 0 0.1rem; }
.mc-role  { font-size: 0.68rem; color: #64748B; }
.mc-kda   { font-size: 0.82rem; font-weight: 600; margin: 0.5rem 0 0.2rem; }
.mc-score { font-size: 1.55rem; font-weight: 800; line-height: 1; }
.mc-tag   { font-size: 0.66rem; margin-top: 0.18rem; }
.mc-pos   { color: #22C55E; }
.mc-neg   { color: #EF4444; }

/* ── Locked screen ──────────────────────────────── */
.locked-screen {
    text-align: center;
    padding: 5rem 2rem;
    max-width: 360px;
    margin: 0 auto;
}
.locked-screen .ls-icon  { font-size: 2.5rem; margin-bottom: 1rem; }
.locked-screen .ls-title { font-size: 1.35rem; font-weight: 700; margin-bottom: 0.75rem; }
.locked-screen .ls-body  { color: #64748B; line-height: 1.7; font-size: 0.95rem; }

/* ── Onboarding steps ───────────────────────────── */
.steps {
    display: flex;
    margin: 1.25rem 0 2rem;
}
.step-item {
    flex: 1;
    text-align: center;
    padding: 0.55rem 0.25rem;
    border-bottom: 2px solid rgba(128,128,128,0.18);
    font-size: 0.72rem;
    color: #64748B;
    font-weight: 500;
}
.step-item.active {
    border-bottom-color: #3B82F6;
    color: #3B82F6;
    font-weight: 700;
}
.step-item.done {
    border-bottom-color: #22C55E;
    color: #22C55E;
}
.step-num {
    display: block;
    font-size: 1rem;
    margin-bottom: 0.15rem;
}

/* ── Player card (config verificada) ───────────── */
.player-card {
    border-radius: 12px;
    padding: 1.5rem 1.75rem;
    border: 1px solid rgba(34,197,94,0.25);
    background: rgba(34,197,94,0.05);
    margin-bottom: 1.5rem;
}
.player-card .pc-name {
    font-size: 1.25rem;
    font-weight: 800;
    margin-bottom: 0.2rem;
}
.player-card .pc-meta {
    font-size: 0.85rem;
    color: #64748B;
    line-height: 1.7;
}

/* ── Next steps list ────────────────────────────── */
.next-steps {
    padding: 1.1rem 1.4rem;
    border-radius: 10px;
    border: 1px solid rgba(128,128,128,0.12);
    background: var(--secondary-background-color);
    margin-bottom: 1rem;
}
.next-steps .ns-item {
    font-size: 0.9rem;
    padding: 0.3rem 0;
    color: #94A3B8;
}
.next-steps .ns-item.done  { color: #22C55E; }
.next-steps .ns-item.current { color: #3B82F6; font-weight: 600; }

/* ── Fade-in ────────────────────────────────────── */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(5px); }
    to   { opacity: 1; transform: translateY(0); }
}
.fade-in { animation: fadeIn 0.35s ease forwards; }
</style>
"""


# ---------------------------------------------------------------------------
# Setup check
# ---------------------------------------------------------------------------

def is_setup_complete() -> bool:
    """
    True cuando la cuenta está vinculada y verificada con Riot API.

    No requiere API Key activa — el análisis histórico de partidas ya
    descargadas funciona sin ella. La key solo se necesita para verificar
    cuenta o descargar partidas nuevas.
    """
    return all([
        db.get_config("game_name"),
        db.get_config("tag_line"),
        db.get_config("platform"),
        db.get_config("puuid"),   # solo existe tras una verificación exitosa
    ])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(
        page_title="LoL Coach",
        page_icon="🎮",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.markdown(_CSS, unsafe_allow_html=True)

    try:
        db.init_db()
    except Exception as e:
        st.error(f"No se pudo inicializar la base de datos: {e}")
        st.stop()

    setup_ok = is_setup_complete()

    # ----------------------------------------------------------------
    # Sidebar
    # ----------------------------------------------------------------
    with st.sidebar:
        st.markdown("### 🎮 LoL Coach")
        st.caption("Entrenamiento personal basado en datos")
        st.divider()

        if setup_ok:
            page = st.radio(
                "nav",
                options=["⚙️ Configuración", "🎮 Partidas", "📊 Análisis"],
                label_visibility="collapsed",
                key="current_page",
            )
        else:
            st.markdown("⚙️ &nbsp; **Configuración**")
            st.markdown(
                '<p style="color:#475569;font-size:0.9rem;margin:0.2rem 0 0">'
                '🔒 &nbsp; Partidas</p>'
                '<p style="color:#475569;font-size:0.9rem;margin:0.2rem 0 0">'
                '🔒 &nbsp; Análisis</p>',
                unsafe_allow_html=True,
            )
            page = "⚙️ Configuración"

        st.divider()

        puuid = db.get_config("puuid")
        if setup_ok and puuid:
            player = db.get_player(puuid)
            if player:
                st.markdown(f"**{player['riot_id']}#{player['tag']}**")
                st.caption(
                    f"{player.get('rank', 'Sin rango')} · {player.get('lp', 0)} LP"
                )
        else:
            st.caption("⚠️ Cuenta no configurada")

    # ----------------------------------------------------------------
    # Routing
    # ----------------------------------------------------------------
    if page == "⚙️ Configuración":
        page_config.render()
    elif page == "🎮 Partidas":
        page_matches.render()
    elif page == "📊 Análisis":
        page_analysis.render()


if __name__ == "__main__":
    main()
