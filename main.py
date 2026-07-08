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

import analytics
import db
import ui.config   as page_config
import ui.matches  as page_matches
import ui.coaching as page_coaching
import ui.draft    as page_draft

# ---------------------------------------------------------------------------
# CSS global
# ---------------------------------------------------------------------------

_CSS = """
<style>
/* ═══════════════════════════════════════════════
   BASE
═══════════════════════════════════════════════ */
.stApp { background-color: #070B14 !important; }
[data-testid="stAppViewContainer"] { background-color: #070B14 !important; }
.main .block-container {
    background-color: #070B14 !important;
    padding-top: 1.25rem !important;
    padding-bottom: 3rem !important;
    max-width: 100% !important;
}
header[data-testid="stHeader"] {
    background: transparent !important;
    border-bottom: none !important;
}
.stApp * { color: inherit; }

/* ═══════════════════════════════════════════════
   SIDEBAR
═══════════════════════════════════════════════ */
[data-testid="stSidebar"] {
    background-color: #0A0F1E !important;
    border-right: 1px solid rgba(255,255,255,0.05) !important;
}
[data-testid="stSidebar"] > div:first-child { padding-top: 1.25rem; }

.sb-logo {
    display: flex; align-items: center; gap: 10px;
    padding: 0 0.5rem 1.25rem;
}
.sb-logo-icon {
    width: 38px; height: 38px;
    background: linear-gradient(135deg,#8B5CF6,#6D28D9);
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.1rem; flex-shrink: 0;
}
.sb-logo-title {
    font-size: 0.82rem; font-weight: 800;
    letter-spacing: 0.06em; color: #FFFFFF; line-height: 1;
}
.sb-logo-sub {
    font-size: 0.58rem; letter-spacing: 0.14em;
    color: #374151; text-transform: uppercase; margin-top: 3px;
}

/* Nav radio */
[data-testid="stSidebar"] .stRadio > div { gap: 2px !important; }
[data-testid="stSidebar"] .stRadio label {
    border-radius: 8px !important;
    padding: 0.62rem 0.9rem !important;
    width: 100% !important;
    color: #4B5563 !important;
    font-size: 0.86rem !important;
    font-weight: 500 !important;
    transition: all 0.15s ease !important;
    cursor: pointer !important;
    border: 1px solid transparent !important;
}
[data-testid="stSidebar"] .stRadio label:hover {
    background: rgba(139,92,246,0.07) !important;
    color: #9CA3AF !important;
}
[data-testid="stSidebar"] .stRadio label[data-checked="true"] {
    background: rgba(139,92,246,0.14) !important;
    color: #8B5CF6 !important;
    font-weight: 700 !important;
    border-color: rgba(139,92,246,0.2) !important;
}
[data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p { margin: 0; }
/* hide default radio dot */
[data-testid="stSidebar"] .stRadio [data-baseweb="radio"] > div:first-child { display: none !important; }

.sb-player-card {
    border-top: 1px solid rgba(255,255,255,0.05);
    padding: 1rem 0.5rem 0.5rem;
    margin-top: 0.5rem;
}
.sb-player-name  { font-size: 0.86rem; font-weight: 700; color: #FFFFFF; }
.sb-player-level { font-size: 0.72rem; color: #374151; margin-top: 1px; }
.sb-player-rank  { font-size: 0.78rem; font-weight: 600; color: #8B5CF6; margin-top: 6px; }
.sb-quote {
    font-size: 0.7rem; color: #1F2937; font-style: italic;
    margin-top: 1.25rem; line-height: 1.5; padding: 0 0.25rem;
}

/* ═══════════════════════════════════════════════
   PAGE HEADER
═══════════════════════════════════════════════ */
.pg-title {
    font-size: 1.55rem; font-weight: 800; color: #FFFFFF; line-height: 1.2;
}
.pg-subtitle { font-size: 0.84rem; color: #374151; margin-top: 3px; }
.pg-sync     { font-size: 0.7rem; color: #1F2937; text-align: right; padding-top: 0.25rem; }

/* ═══════════════════════════════════════════════
   CARD BASE
═══════════════════════════════════════════════ */
.card {
    background: #0E1525;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px;
    padding: 1.25rem 1.4rem;
    position: relative; overflow: hidden;
    transition: border-color 0.2s ease;
    height: 100%;
}
.card:hover { border-color: rgba(139,92,246,0.18); }
.card-label {
    font-size: 0.58rem; font-weight: 700; letter-spacing: 0.18em;
    text-transform: uppercase; color: #1F2937; margin-bottom: 0.85rem;
}

/* ═══════════════════════════════════════════════
   LEVEL CARD
═══════════════════════════════════════════════ */
.level-tier {
    font-size: 1.7rem; font-weight: 900;
    letter-spacing: -0.02em; line-height: 1;
}
.level-sub    { font-size: 0.7rem; color: #374151; margin-top: 0.75rem; }
.level-pct    { font-size: 0.75rem; color: #4B5563; }

/* ═══════════════════════════════════════════════
   TREND CARD
═══════════════════════════════════════════════ */
.trend-delta { font-size: 2.4rem; font-weight: 900; line-height: 1; }
.trend-vs    { font-size: 0.7rem; color: #374151; margin-top: 3px; }

/* ═══════════════════════════════════════════════
   OBJETIVO SEMANAL CARD
═══════════════════════════════════════════════ */
.goal-card {
    background: #0E1525;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px;
    padding: 1.25rem 1.4rem;
}
.goal-title {
    font-size: 1.25rem; font-weight: 900; color: #FFFFFF;
    letter-spacing: -0.01em; line-height: 1.2; margin-bottom: 1rem;
}
.goal-row {
    display: flex; align-items: center;
    gap: 1rem; margin: 0.5rem 0 0.75rem;
}
.goal-current { font-size: 2rem; font-weight: 900; color: #EF4444; line-height: 1; }
.goal-arrow   { font-size: 1.2rem; color: #374151; }
.goal-target  { font-size: 2rem; font-weight: 900; color: #22C55E; line-height: 1; }
.goal-bar-track {
    height: 7px; background: rgba(255,255,255,0.05);
    border-radius: 99px; overflow: hidden; margin: 0.5rem 0 0.6rem;
}
.goal-bar-fill {
    height: 100%; border-radius: 99px;
    background: linear-gradient(90deg, #EF4444 0%, #F59E0B 50%, #22C55E 100%);
}
.goal-meta {
    display: flex; justify-content: space-between;
    font-size: 0.7rem; color: #374151;
}
.goal-meta-val { font-weight: 700; color: #EF4444; }

/* ═══════════════════════════════════════════════
   PROBLEMA PRINCIPAL
═══════════════════════════════════════════════ */
.problem-card {
    background: linear-gradient(135deg, rgba(127,29,29,0.35), rgba(14,21,37,0.95));
    border: 1px solid rgba(239,68,68,0.2);
    border-radius: 14px;
    padding: 1.5rem;
    position: relative; overflow: hidden;
}
.problem-card::after {
    content: '';
    position: absolute; top: -50px; right: -50px;
    width: 180px; height: 180px;
    background: radial-gradient(circle, rgba(239,68,68,0.07), transparent 70%);
    pointer-events: none;
}
.problem-label {
    font-size: 0.58rem; font-weight: 700; letter-spacing: 0.2em;
    text-transform: uppercase; color: #EF4444; margin-bottom: 0.4rem;
}
.problem-title {
    font-size: 1.7rem; font-weight: 900; color: #FFFFFF;
    letter-spacing: -0.02em; line-height: 1.1; margin-bottom: 0.85rem;
}
.problem-main-stat { font-size: 2.6rem; font-weight: 900; color: #EF4444; line-height: 1; }
.problem-main-sub  { font-size: 0.7rem; color: #4B5563; margin-top: 2px; }
.problem-cmp {
    display: flex; gap: 1.5rem; margin-top: 0.75rem;
}
.problem-cmp-col { display: flex; flex-direction: column; gap: 2px; }
.problem-cmp-val-w { font-size: 1.05rem; font-weight: 700; color: #22C55E; }
.problem-cmp-val-l { font-size: 1.05rem; font-weight: 700; color: #EF4444; }
.problem-cmp-lbl   { font-size: 0.63rem; color: #374151; }
.problem-desc {
    font-size: 0.82rem; color: #4B5563; line-height: 1.6;
    margin-top: 1rem; padding-top: 0.75rem;
    border-top: 1px solid rgba(255,255,255,0.04);
}

/* ═══════════════════════════════════════════════
   PLAN DE ENTRENAMIENTO
═══════════════════════════════════════════════ */
.plan-card {
    background: #0E1525;
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px;
    padding: 1.5rem;
}
.plan-main { display: flex; gap: 1.25rem; align-items: flex-start; }
.plan-icon-box {
    width: 60px; height: 60px; min-width: 60px;
    background: linear-gradient(135deg, rgba(239,68,68,0.2), rgba(127,29,29,0.35));
    border: 1px solid rgba(239,68,68,0.15);
    border-radius: 12px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.7rem;
}
.plan-action-lbl {
    font-size: 0.58rem; font-weight: 700; letter-spacing: 0.14em;
    text-transform: uppercase; color: #374151; margin-bottom: 0.4rem;
}
.plan-action-text { font-size: 0.96rem; font-weight: 700; color: #FFFFFF; line-height: 1.5; }
.plan-sec { margin-top: 1.1rem; padding-top: 1.1rem; border-top: 1px solid rgba(255,255,255,0.04); }
.plan-sec-lbl {
    font-size: 0.58rem; font-weight: 700; letter-spacing: 0.14em;
    text-transform: uppercase; color: #374151; margin-bottom: 0.6rem;
}
.plan-sec-item {
    display: flex; align-items: flex-start; gap: 10px;
    padding: 0.5rem 0;
    font-size: 0.82rem; color: #4B5563;
    border-bottom: 1px solid rgba(255,255,255,0.03);
    line-height: 1.5;
}
.plan-sec-item:last-child { border-bottom: none; }
.plan-sec-icon { font-size: 0.85rem; margin-top: 1px; min-width: 18px; }

/* ═══════════════════════════════════════════════
   FORTALEZAS / DEBILIDADES
═══════════════════════════════════════════════ */
.str-item, .wk-item {
    display: flex; align-items: flex-start; gap: 12px;
    padding: 0.8rem; border-radius: 10px; margin-bottom: 0.5rem;
}
.str-item { background: rgba(34,197,94,0.05); border: 1px solid rgba(34,197,94,0.1); }
.wk-item  { background: rgba(239,68,68,0.05); border: 1px solid rgba(239,68,68,0.1); }
.str-icon, .wk-icon {
    width: 34px; height: 34px; min-width: 34px; border-radius: 8px;
    display: flex; align-items: center; justify-content: center; font-size: 0.95rem;
}
.str-icon { background: rgba(34,197,94,0.1); }
.wk-icon  { background: rgba(239,68,68,0.1); }
.str-name { font-size: 0.75rem; font-weight: 700; color: #22C55E; margin-bottom: 2px; }
.wk-name  { font-size: 0.75rem; font-weight: 700; color: #F59E0B; margin-bottom: 2px; }
.str-evidence, .wk-evidence { font-size: 0.7rem; color: #374151; line-height: 1.4; }

/* ═══════════════════════════════════════════════
   RESUMEN PARTIDAS (right column)
═══════════════════════════════════════════════ */
.match-row {
    display: flex; align-items: center; gap: 10px;
    padding: 0.55rem 0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
}
.match-row:last-child { border-bottom: none; }
.match-row-result { font-size: 0.68rem; font-weight: 700; width: 56px; min-width: 56px; }
.result-win  { color: #22C55E; }
.result-loss { color: #EF4444; }
.match-row-info { flex: 1; }
.match-row-champ { font-size: 0.78rem; font-weight: 600; color: #D1D5DB; }
.match-row-kda   { font-size: 0.68rem; color: #374151; }
.match-row-score { font-size: 0.88rem; font-weight: 800; }

/* ═══════════════════════════════════════════════
   METRIC CARDS (datos avanzados)
═══════════════════════════════════════════════ */
.metric-card {
    background: #0E1525; border: 1px solid rgba(255,255,255,0.05);
    border-radius: 10px; padding: 0.85rem 1rem;
}
.metric-lbl {
    font-size: 0.56rem; font-weight: 700; letter-spacing: 0.15em;
    text-transform: uppercase; color: #1F2937; margin-bottom: 0.3rem;
}
.metric-val { font-size: 1.4rem; font-weight: 800; color: #FFFFFF; line-height: 1; }
.metric-pct { font-size: 0.66rem; color: #374151; margin: 0.25rem 0 0.45rem; }
.metric-bar { height: 3px; background: rgba(255,255,255,0.05); border-radius: 99px; overflow: hidden; }
.metric-bar-fill { height: 100%; background: #8B5CF6; border-radius: 99px; }

/* ═══════════════════════════════════════════════
   SESSION ALERT
═══════════════════════════════════════════════ */
.session-alert {
    background: rgba(245,158,11,0.07);
    border: 1px solid rgba(245,158,11,0.2);
    border-left: 3px solid #F59E0B;
    border-radius: 10px; padding: 0.9rem 1.2rem;
    margin-bottom: 1.25rem;
    display: flex; align-items: flex-start; gap: 12px;
}
.session-alert-icon { font-size: 1.1rem; }
.session-alert-title { font-size: 0.76rem; font-weight: 700; color: #F59E0B; margin-bottom: 2px; }
.session-alert-body  { font-size: 0.76rem; color: #4B5563; line-height: 1.5; }

/* ═══════════════════════════════════════════════
   SECTION HEADERS
═══════════════════════════════════════════════ */
.sec-header {
    display: flex; align-items: center; gap: 8px;
    margin: 1.5rem 0 0.85rem;
    padding-bottom: 0.65rem;
    border-bottom: 1px solid rgba(255,255,255,0.04);
}
.sec-header-title {
    font-size: 0.66rem; font-weight: 700; letter-spacing: 0.14em;
    text-transform: uppercase; color: #374151;
}

/* ═══════════════════════════════════════════════
   INFO BAR (bottom)
═══════════════════════════════════════════════ */
.info-bar {
    position: fixed; bottom: 0; left: 0; right: 0;
    background: rgba(7,11,20,0.94);
    border-top: 1px solid rgba(255,255,255,0.05);
    padding: 0.55rem 1.5rem;
    font-size: 0.73rem; color: #374151;
    display: flex; align-items: center; gap: 8px;
    z-index: 999; backdrop-filter: blur(8px);
}

/* ═══════════════════════════════════════════════
   STREAMLIT COMPONENT OVERRIDES
═══════════════════════════════════════════════ */
.stSelectbox > div > div {
    background-color: #0E1525 !important;
    border-color: rgba(255,255,255,0.08) !important;
    border-radius: 8px !important;
    color: #FFFFFF !important;
}
[data-testid="stMetric"] {
    background: #0E1525;
    border-radius: 10px; padding: 0.75rem 1rem;
    border: 1px solid rgba(255,255,255,0.06);
}
[data-testid="stMetricValue"] { color: #FFFFFF !important; }
.stTextInput > div > div > input {
    background-color: #0E1525 !important;
    border-color: rgba(255,255,255,0.08) !important;
    color: #FFFFFF !important; border-radius: 8px !important;
}
.stButton > button { border-radius: 8px !important; font-weight: 600 !important; }
hr { border-color: rgba(255,255,255,0.05) !important; }
.streamlit-expanderHeader {
    background-color: #0E1525 !important; border-radius: 8px !important;
}
[data-testid="stDataFrame"] { border-radius: 10px !important; }
[data-testid="stAlert"] { border-radius: 10px !important; }
p, .stMarkdown p { color: #9CA3AF; }
h1, h2, h3 { color: #FFFFFF !important; }

/* ═══════════════════════════════════════════════
   ETIQUETAS COMPARTIDAS
═══════════════════════════════════════════════ */
.score-label { font-size: 0.8rem; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; margin-top: 0.85rem; }
.sec-label {
    font-size: 0.65rem; font-weight: 700; letter-spacing: 0.16em;
    text-transform: uppercase; color: #374151;
    margin: 2rem 0 0.85rem; padding-bottom: 0.5rem;
    border-bottom: 1px solid rgba(255,255,255,0.05);
}
.mc {
    background: #0E1525; border-radius: 12px; padding: 1rem 0.75rem 0.85rem;
    text-align: center; border: 1px solid rgba(255,255,255,0.06); height: 100%;
}
.mc-win  { border-top: 3px solid #22C55E; }
.mc-loss { border-top: 3px solid #EF4444; }
.mc-res  { font-size: 0.62rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; }
.mc-res-win  { color: #22C55E; }
.mc-res-loss { color: #EF4444; }
.mc-champ { font-size: 0.95rem; font-weight: 700; margin: 0.35rem 0 0.1rem; color: #FFFFFF; }
.mc-role  { font-size: 0.68rem; color: #374151; }
.mc-kda   { font-size: 0.82rem; font-weight: 600; margin: 0.5rem 0 0.2rem; color: #D1D5DB; }
.mc-score { font-size: 1.55rem; font-weight: 800; line-height: 1; }
.mc-tag   { font-size: 0.66rem; margin-top: 0.18rem; }
.mc-pos   { color: #22C55E; }
.mc-neg   { color: #EF4444; }
.player-card {
    border-radius: 12px; padding: 1.5rem 1.75rem;
    border: 1px solid rgba(34,197,94,0.25); background: rgba(34,197,94,0.05); margin-bottom: 1.5rem;
}
.player-card .pc-name { font-size: 1.25rem; font-weight: 800; margin-bottom: 0.2rem; color: #FFFFFF; }
.player-card .pc-meta { font-size: 0.85rem; color: #374151; line-height: 1.7; }
.next-steps { padding: 1.1rem 1.4rem; border-radius: 10px; border: 1px solid rgba(255,255,255,0.06); background: #0E1525; margin-bottom: 1rem; }
.next-steps .ns-item    { font-size: 0.9rem; padding: 0.3rem 0; color: #4B5563; }
.next-steps .ns-item.done    { color: #22C55E; }
.next-steps .ns-item.current { color: #3B82F6; font-weight: 600; }
.steps { display: flex; margin: 1.25rem 0 2rem; }
.step-item {
    flex: 1; text-align: center; padding: 0.55rem 0.25rem;
    border-bottom: 2px solid rgba(255,255,255,0.07);
    font-size: 0.72rem; color: #374151; font-weight: 500;
}
.step-item.active { border-bottom-color: #3B82F6; color: #3B82F6; font-weight: 700; }
.step-item.done   { border-bottom-color: #22C55E; color: #22C55E; }
.step-num { display: block; font-size: 1rem; margin-bottom: 0.15rem; }
.locked-screen { text-align: center; padding: 5rem 2rem; max-width: 360px; margin: 0 auto; }
.locked-screen .ls-icon  { font-size: 2.5rem; margin-bottom: 1rem; }
.locked-screen .ls-title { font-size: 1.35rem; font-weight: 700; margin-bottom: 0.75rem; color: #FFFFFF; }
.locked-screen .ls-body  { color: #374151; line-height: 1.7; font-size: 0.95rem; }

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
}
.fade-in { animation: fadeIn 0.4s ease forwards; }

/* ═══════════════════════════════════════════════
   DRAFT — CHAMP SELECT
═══════════════════════════════════════════════ */
.draft-status {
    display: flex; align-items: center; gap: 1rem;
    background: #0E1525; border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px; padding: 0.85rem 1.2rem; margin-bottom: 1.5rem;
    font-size: 0.8rem;
}
.draft-status-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.draft-status-dot.connected    { background: #22C55E; box-shadow: 0 0 6px #22C55E; }
.draft-status-dot.disconnected { background: #EF4444; }
.draft-status-dot.idle         { background: #F59E0B; }
.draft-status-label  { font-weight: 700; color: #D1D5DB; }
.draft-status-detail { color: #374151; margin-left: 0.25rem; }
.draft-status-phase  {
    margin-left: auto; font-size: 0.72rem; font-weight: 700;
    letter-spacing: 0.1em; text-transform: uppercase;
}
.draft-team-header {
    font-size: 0.65rem; font-weight: 700; letter-spacing: 0.16em;
    text-transform: uppercase; color: #374151;
    padding-bottom: 0.5rem; margin-bottom: 0.75rem;
    border-bottom: 1px solid rgba(255,255,255,0.05);
}
.draft-slot {
    display: flex; align-items: center; gap: 0.75rem;
    padding: 0.55rem 0.85rem; border-radius: 8px; margin-bottom: 0.35rem;
    background: #0E1525; border: 1px solid rgba(255,255,255,0.04); min-height: 42px;
}
.draft-slot.me    { border-color: #8B5CF6; background: rgba(139,92,246,0.06); }
.draft-slot.enemy { border-color: rgba(239,68,68,0.15); background: rgba(239,68,68,0.03); }
.draft-slot-pos {
    font-size: 0.62rem; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: #4B5563; min-width: 28px;
}
.draft-slot-champ { font-size: 0.88rem; font-weight: 700; color: #D1D5DB; flex: 1; }
.draft-slot-champ.empty { color: #1F2937; font-weight: 400; font-style: italic; }
.draft-slot-me-tag {
    font-size: 0.58rem; font-weight: 700; letter-spacing: 0.12em;
    text-transform: uppercase; color: #8B5CF6;
    background: rgba(139,92,246,0.12); padding: 2px 7px; border-radius: 4px;
}
.draft-bans { margin-top: 0.5rem; display: flex; flex-wrap: wrap; gap: 0.4rem; }
.draft-ban-chip {
    font-size: 0.72rem; font-weight: 600; color: #4B5563;
    background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.18);
    padding: 2px 9px; border-radius: 5px;
}
.draft-no-bans { font-size: 0.75rem; color: #1F2937; font-style: italic; }
.draft-timer-bar {
    display: flex; align-items: center; gap: 1rem;
    background: #0E1525; border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px; padding: 0.7rem 1.1rem; margin-bottom: 1rem;
}
.draft-timer-phase { font-size: 0.72rem; font-weight: 700;
    letter-spacing: 0.12em; text-transform: uppercase; color: #374151; }
.draft-timer-sec   { font-size: 1.4rem; font-weight: 900; color: #FFFFFF; min-width: 52px; }
.draft-timer-sec.urgent { color: #EF4444; }
.draft-waiting { text-align: center; padding: 3rem 1rem; color: #374151; }
.draft-waiting-icon  { font-size: 2.5rem; margin-bottom: 1rem; }
.draft-waiting-title { font-size: 1rem; font-weight: 700; color: #4B5563; margin-bottom: 0.4rem; }
.draft-waiting-body  { font-size: 0.8rem; line-height: 1.6; }

/* ── Draft Intelligence ── */
.di-score-card {
    background: #0E1525; border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px; padding: 1rem 1.25rem; margin-bottom: 1rem;
}
.di-score-header {
    display: flex; align-items: baseline; gap: 0.75rem; margin-bottom: 0.9rem;
}
.di-score-champion { font-size: 1rem; font-weight: 800; color: #FFFFFF; }
.di-score-grade    { font-size: 1.6rem; font-weight: 900; line-height: 1; }
.di-score-total    { font-size: 0.75rem; color: #374151; }
.di-score-label    { font-size: 0.62rem; font-weight: 700; letter-spacing: 0.14em;
    text-transform: uppercase; color: #4B5563; }
.di-factor-row {
    display: flex; align-items: center; gap: 0.6rem;
    margin-bottom: 0.45rem; font-size: 0.75rem;
}
.di-factor-label { color: #4B5563; min-width: 90px; }
.di-factor-bar-wrap {
    flex: 1; height: 5px; background: rgba(255,255,255,0.05);
    border-radius: 3px; overflow: hidden;
}
.di-factor-bar-fill { height: 100%; border-radius: 3px; }
.di-factor-pts { color: #374151; min-width: 40px; text-align: right; }

.di-rec-row {
    display: flex; align-items: center; gap: 0.65rem;
    padding: 0.65rem 0.9rem; border-radius: 8px; margin-bottom: 0.4rem;
    background: #0E1525; border: 1px solid rgba(255,255,255,0.04);
}
.di-rec-rank  { font-size: 0.78rem; font-weight: 900; color: #374151; min-width: 18px; }
.di-rec-champ { font-size: 0.9rem; font-weight: 800; color: #FFFFFF; flex: 1.2; }
.di-rec-stats { font-size: 0.75rem; color: #4B5563; flex: 1.8; }
.di-rec-tag   {
    font-size: 0.56rem; font-weight: 700; letter-spacing: 0.14em;
    text-transform: uppercase; padding: 2px 7px; border-radius: 4px;
}
.di-rec-tag.CARRY   { color: #22C55E; background: rgba(34,197,94,0.1); }
.di-rec-tag.COMFORT { color: #3B82F6; background: rgba(59,130,246,0.1); }
.di-rec-tag.MAIN    { color: #8B5CF6; background: rgba(139,92,246,0.1); }
.di-rec-tag.SOLID   { color: #F59E0B; background: rgba(245,158,11,0.1); }
.di-rec-conf { font-size: 0.7rem; color: #374151; min-width: 54px; text-align: right; }

.di-avoid-row {
    display: flex; align-items: center; gap: 0.65rem;
    padding: 0.55rem 0.9rem; border-radius: 8px; margin-bottom: 0.35rem;
    background: rgba(239,68,68,0.04); border: 1px solid rgba(239,68,68,0.12);
}
.di-avoid-champ { font-size: 0.87rem; font-weight: 700; color: #EF4444; flex: 1; }
.di-avoid-stats { font-size: 0.75rem; color: #4B5563; }

.di-warn-row {
    display: flex; gap: 0.6rem; align-items: flex-start;
    padding: 0.55rem 0.85rem; border-radius: 8px; margin-bottom: 0.4rem;
    font-size: 0.78rem; line-height: 1.5;
}
.di-warn-row.critical { background: rgba(239,68,68,0.07); border: 1px solid rgba(239,68,68,0.18); }
.di-warn-row.warning  { background: rgba(245,158,11,0.06); border: 1px solid rgba(245,158,11,0.15); }
.di-warn-row.info     { background: rgba(59,130,246,0.05); border: 1px solid rgba(59,130,246,0.12); }
.di-warn-icon { min-width: 18px; }
.di-warn-text { color: #4B5563; }

/* ═══════════════════════════════════════════════
   CHAMPION INTELLIGENCE
═══════════════════════════════════════════════ */
.ci-grade-bar {
    display: flex; align-items: center; gap: 1.5rem;
    background: #0E1525; border: 1px solid rgba(255,255,255,0.06);
    border-radius: 14px; padding: 1.1rem 1.5rem; margin-bottom: 1rem;
}
.ci-grade-letter {
    font-size: 3rem; font-weight: 900; line-height: 1; min-width: 48px; text-align: center;
}
.ci-grade-label  { font-size: 0.7rem; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; }
.ci-grade-score  { font-size: 0.78rem; color: #374151; margin-top: 2px; }
.ci-grade-desc   { font-size: 0.8rem; color: #4B5563; line-height: 1.5; }

.ci-class-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.75rem; margin-bottom: 1rem; }
.ci-class-card {
    background: #0E1525; border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px; padding: 1rem 1.15rem;
}
.ci-class-card.main    { border-left: 3px solid #8B5CF6; }
.ci-class-card.carry   { border-left: 3px solid #22C55E; }
.ci-class-card.comfort { border-left: 3px solid #3B82F6; }
.ci-class-card.trap    { border-left: 3px solid #EF4444; background: rgba(239,68,68,0.04); }
.ci-class-tag  {
    font-size: 0.56rem; font-weight: 700; letter-spacing: 0.16em;
    text-transform: uppercase; margin-bottom: 0.35rem;
}
.ci-class-tag.main    { color: #8B5CF6; }
.ci-class-tag.carry   { color: #22C55E; }
.ci-class-tag.comfort { color: #3B82F6; }
.ci-class-tag.trap    { color: #EF4444; }
.ci-class-name { font-size: 1.05rem; font-weight: 800; color: #FFFFFF; margin-bottom: 0.35rem; }
.ci-class-meta { font-size: 0.7rem; color: #374151; }

.ci-champ-row {
    display: flex; align-items: center; gap: 0;
    padding: 0.6rem 0; border-bottom: 1px solid rgba(255,255,255,0.04);
}
.ci-champ-row:last-child { border-bottom: none; }
.ci-champ-name { font-size: 0.85rem; font-weight: 700; color: #D1D5DB; flex: 1.4; }
.ci-champ-games{ font-size: 0.78rem; color: #374151; flex: 0.6; }
.ci-champ-wr   { font-size: 0.85rem; font-weight: 700; flex: 0.8; }
.ci-champ-score{ font-size: 0.85rem; font-weight: 700; color: #FFFFFF; flex: 0.8; }
.ci-champ-trend{ font-size: 0.85rem; font-weight: 700; flex: 0.5; text-align: right; }

.ci-insight {
    display: flex; align-items: flex-start; gap: 10px;
    padding: 0.65rem 0.9rem; border-radius: 8px; margin-bottom: 0.5rem;
    font-size: 0.78rem; line-height: 1.5;
}
.ci-insight.warning  { background: rgba(239,68,68,0.06); border: 1px solid rgba(239,68,68,0.15); }
.ci-insight.info     { background: rgba(59,130,246,0.05); border: 1px solid rgba(59,130,246,0.12); }
.ci-insight.positive { background: rgba(34,197,94,0.05); border: 1px solid rgba(34,197,94,0.12); }
.ci-insight-icon { font-size: 0.85rem; min-width: 18px; margin-top: 1px; }
.ci-insight-text { color: #4B5563; }
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
        st.markdown(
            '<div class="sb-logo">'
            '<div class="sb-logo-icon">⚡</div>'
            '<div><div class="sb-logo-title">LOL COACH</div>'
            '<div class="sb-logo-sub">Tu mejor versión</div></div>'
            '</div>',
            unsafe_allow_html=True,
        )

        if setup_ok:
            page = st.radio(
                "nav",
                options=["🧠 Coaching", "🎮 Partidas", "🎯 Draft", "⚙️ Configuración"],
                label_visibility="collapsed",
                key="current_page",
            )
        else:
            st.markdown(
                '<p style="color:#374151;font-size:0.86rem;padding:0.62rem 0.9rem;font-weight:600">⚙️ Configuración</p>'
                '<p style="color:#1F2937;font-size:0.86rem;padding:0.4rem 0.9rem">🔒 Coaching</p>'
                '<p style="color:#1F2937;font-size:0.86rem;padding:0.4rem 0.9rem">🔒 Partidas</p>'
                '<p style="color:#1F2937;font-size:0.86rem;padding:0.4rem 0.9rem">🔒 Draft</p>',
                unsafe_allow_html=True,
            )
            page = "⚙️ Configuración"

        puuid = db.get_config("puuid")
        if setup_ok and puuid:
            player = db.get_player(puuid)
            if player:
                rank  = player.get("rank", "Sin rango")
                lp    = player.get("lp", 0)
                level = player.get("level", "?")
                st.markdown(
                    f'<div class="sb-player-card">'
                    f'<div class="sb-player-name">👤 {player["riot_id"]}#{player["tag"]}</div>'
                    f'<div class="sb-player-level">Nivel {level}</div>'
                    f'<div class="sb-player-rank">{rank} · {lp} LP</div>'
                    f'<div class="sb-quote">"La mejora es un proceso diario,<br>no un destino."<br><br>— LoL Coach</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown('<p style="color:#374151;font-size:0.78rem;padding:0.5rem">⚠️ Cuenta no configurada</p>', unsafe_allow_html=True)

    # ----------------------------------------------------------------
    # Instrumentación local (Sprint 2) — solo local, sin datos personales
    # ----------------------------------------------------------------
    analytics.track_screen(page)

    # ----------------------------------------------------------------
    # Routing
    # ----------------------------------------------------------------
    if page == "🧠 Coaching":
        page_coaching.render()
    elif page == "🎮 Partidas":
        page_matches.render()
    elif page == "🎯 Draft":
        page_draft.render()
    elif page == "⚙️ Configuración":
        page_config.render()


if __name__ == "__main__":
    main()
