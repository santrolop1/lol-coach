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
import ui.config      as page_config
import ui.matches     as page_matches
import ui.coaching    as page_coaching
import ui.draft       as page_draft
import ui.onboarding  as page_onboarding
from backend.services.setup_service import is_setup_complete
from backend.services import sync_service

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
    color: #6B7280; text-transform: uppercase; margin-top: 3px;
}

/* Nav radio */
[data-testid="stSidebar"] .stRadio > div { gap: 2px !important; }
[data-testid="stSidebar"] .stRadio label {
    border-radius: 8px !important;
    padding: 0.62rem 0.9rem !important;
    width: 100% !important;
    color: #D1D5DB !important;
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
.sb-player-level { font-size: 0.72rem; color: #6B7280; margin-top: 1px; }
.sb-player-rank  { font-size: 0.78rem; font-weight: 600; color: #8B5CF6; margin-top: 6px; }
.sb-quote {
    font-size: 0.7rem; color: #6B7280; font-style: italic;
    margin-top: 1.25rem; line-height: 1.5; padding: 0 0.25rem;
}

/* ═══════════════════════════════════════════════
   PAGE HEADER
═══════════════════════════════════════════════ */
.pg-title {
    font-size: 1.55rem; font-weight: 800; color: #FFFFFF; line-height: 1.2;
}
.pg-subtitle { font-size: 0.84rem; color: #6B7280; margin-top: 3px; }
.pg-sync     { font-size: 0.7rem; color: #6B7280; text-align: right; padding-top: 0.25rem; }

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
    text-transform: uppercase; color: #6B7280; margin-bottom: 0.85rem;
}

/* ═══════════════════════════════════════════════
   LEVEL CARD
═══════════════════════════════════════════════ */
.level-tier {
    font-size: 1.7rem; font-weight: 900;
    letter-spacing: -0.02em; line-height: 1;
}
.level-sub    { font-size: 0.7rem; color: #6B7280; margin-top: 0.75rem; }
.level-pct    { font-size: 0.75rem; color: #9CA3AF; }

/* ═══════════════════════════════════════════════
   TREND CARD
═══════════════════════════════════════════════ */
.trend-delta { font-size: 2.4rem; font-weight: 900; line-height: 1; }
.trend-vs    { font-size: 0.7rem; color: #6B7280; margin-top: 3px; }

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
.goal-arrow   { font-size: 1.2rem; color: #6B7280; }
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
    font-size: 0.7rem; color: #6B7280;
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
.problem-main-sub  { font-size: 0.7rem; color: #9CA3AF; margin-top: 2px; }
.problem-cmp {
    display: flex; gap: 1.5rem; margin-top: 0.75rem;
}
.problem-cmp-col { display: flex; flex-direction: column; gap: 2px; }
.problem-cmp-val-w { font-size: 1.05rem; font-weight: 700; color: #22C55E; }
.problem-cmp-val-l { font-size: 1.05rem; font-weight: 700; color: #EF4444; }
.problem-cmp-lbl   { font-size: 0.63rem; color: #6B7280; }
.problem-desc {
    font-size: 0.82rem; color: #9CA3AF; line-height: 1.6;
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
    text-transform: uppercase; color: #6B7280; margin-bottom: 0.4rem;
}
.plan-action-text { font-size: 0.96rem; font-weight: 700; color: #FFFFFF; line-height: 1.5; }
.plan-sec { margin-top: 1.1rem; padding-top: 1.1rem; border-top: 1px solid rgba(255,255,255,0.04); }
.plan-sec-lbl {
    font-size: 0.58rem; font-weight: 700; letter-spacing: 0.14em;
    text-transform: uppercase; color: #6B7280; margin-bottom: 0.6rem;
}
.plan-sec-item {
    display: flex; align-items: flex-start; gap: 10px;
    padding: 0.5rem 0;
    font-size: 0.82rem; color: #9CA3AF;
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
.str-evidence, .wk-evidence { font-size: 0.7rem; color: #6B7280; line-height: 1.4; }

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
.match-row-kda   { font-size: 0.68rem; color: #6B7280; }
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
    text-transform: uppercase; color: #6B7280; margin-bottom: 0.3rem;
}
.metric-val { font-size: 1.4rem; font-weight: 800; color: #FFFFFF; line-height: 1; }
.metric-pct { font-size: 0.66rem; color: #6B7280; margin: 0.25rem 0 0.45rem; }
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
.session-alert-body  { font-size: 0.76rem; color: #9CA3AF; line-height: 1.5; }

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
    text-transform: uppercase; color: #6B7280;
}

/* ═══════════════════════════════════════════════
   INFO BAR (bottom)
═══════════════════════════════════════════════ */
.info-bar {
    position: fixed; bottom: 0; left: 0; right: 0;
    background: rgba(7,11,20,0.94);
    border-top: 1px solid rgba(255,255,255,0.05);
    padding: 0.55rem 1.5rem;
    font-size: 0.73rem; color: #6B7280;
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
   LEGACY — config.py
═══════════════════════════════════════════════ */
.score-hero {
    text-align: center; padding: 2.5rem 1rem 2rem;
    border-radius: 14px; border: 1px solid rgba(255,255,255,0.06);
    background: #0E1525; margin-bottom: 1.5rem;
}
.score-value { font-size: 5.5rem; font-weight: 800; letter-spacing: -4px; line-height: 1; }
.score-denom { font-size: 2rem; font-weight: 300; color: #6B7280; letter-spacing: 0; }
.score-label { font-size: 0.8rem; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; margin-top: 0.85rem; }
.sec-label {
    font-size: 0.65rem; font-weight: 700; letter-spacing: 0.16em;
    text-transform: uppercase; color: #6B7280;
    margin: 2rem 0 0.85rem; padding-bottom: 0.5rem;
    border-bottom: 1px solid rgba(255,255,255,0.05);
}
.veredicto {
    padding: 1.2rem 1.5rem; border-radius: 10px;
    border: 1px solid rgba(255,255,255,0.06); background: #0E1525;
    font-size: 1rem; line-height: 1.8; margin-bottom: 0.5rem; color: #9CA3AF;
}
.obj-card {
    border-radius: 10px; padding: 1.4rem 1.6rem;
    border: 1px solid rgba(59,130,246,0.3); border-left: 3px solid #3B82F6;
    background: rgba(59,130,246,0.07); margin-bottom: 1rem;
}
.obj-card .oc-label { font-size: 0.65rem; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: #3B82F6; margin-bottom: 0.45rem; }
.obj-card .oc-goal  { font-size: 1.15rem; font-weight: 700; line-height: 1.3; margin-bottom: 0.45rem; color: #FFFFFF; }
.obj-card .oc-action { font-size: 0.88rem; color: #9CA3AF; line-height: 1.65; }
.coach-card {
    border-radius: 10px; padding: 1.2rem 1.4rem; margin-bottom: 0.75rem;
    border: 1px solid rgba(255,255,255,0.06); background: #0E1525;
}
.coach-card .cc-label { font-size: 0.62rem; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase; color: #6B7280; margin-bottom: 0.35rem; }
.coach-card .cc-stat  { font-size: 1.45rem; font-weight: 700; line-height: 1.1; margin-bottom: 0.25rem; }
.coach-card .cc-body  { font-size: 0.86rem; color: #9CA3AF; line-height: 1.6; }
.coach-card .cc-row   { margin-top: 0.5rem; font-size: 0.82rem; line-height: 1.55; }
.coach-card .cc-cause  { color: #9CA3AF; font-style: italic; }
.coach-card .cc-action { color: #6B7280; }
.strength-card { border-left: 3px solid #F59E0B; }
.weakness-card  { border-left: 3px solid #EF4444; }
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
.mc-role  { font-size: 0.68rem; color: #6B7280; }
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
.player-card .pc-meta { font-size: 0.85rem; color: #6B7280; line-height: 1.7; }
.next-steps { padding: 1.1rem 1.4rem; border-radius: 10px; border: 1px solid rgba(255,255,255,0.06); background: #0E1525; margin-bottom: 1rem; }
.next-steps .ns-item    { font-size: 0.9rem; padding: 0.3rem 0; color: #9CA3AF; }
.next-steps .ns-item.done    { color: #22C55E; }
.next-steps .ns-item.current { color: #3B82F6; font-weight: 600; }
.steps { display: flex; margin: 1.25rem 0 2rem; }
.step-item {
    flex: 1; text-align: center; padding: 0.55rem 0.25rem;
    border-bottom: 2px solid rgba(255,255,255,0.07);
    font-size: 0.72rem; color: #6B7280; font-weight: 500;
}
.step-item.active { border-bottom-color: #3B82F6; color: #3B82F6; font-weight: 700; }
.step-item.done   { border-bottom-color: #22C55E; color: #22C55E; }
.step-num { display: block; font-size: 1rem; margin-bottom: 0.15rem; }
.locked-screen { text-align: center; padding: 5rem 2rem; max-width: 360px; margin: 0 auto; }
.locked-screen .ls-icon  { font-size: 2.5rem; margin-bottom: 1rem; }
.locked-screen .ls-title { font-size: 1.35rem; font-weight: 700; margin-bottom: 0.75rem; color: #FFFFFF; }
.locked-screen .ls-body  { color: #6B7280; line-height: 1.7; font-size: 0.95rem; }

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
.draft-status-detail { color: #6B7280; margin-left: 0.25rem; }
.draft-status-phase  {
    margin-left: auto; font-size: 0.72rem; font-weight: 700;
    letter-spacing: 0.1em; text-transform: uppercase;
}
.draft-team-header {
    font-size: 0.65rem; font-weight: 700; letter-spacing: 0.16em;
    text-transform: uppercase; color: #6B7280;
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
    text-transform: uppercase; color: #9CA3AF; min-width: 28px;
}
.draft-slot-champ { font-size: 0.88rem; font-weight: 700; color: #D1D5DB; flex: 1; }
.draft-slot-champ.empty { color: #6B7280; font-weight: 400; font-style: italic; }
.draft-slot-me-tag {
    font-size: 0.58rem; font-weight: 700; letter-spacing: 0.12em;
    text-transform: uppercase; color: #8B5CF6;
    background: rgba(139,92,246,0.12); padding: 2px 7px; border-radius: 4px;
}
.draft-bans { margin-top: 0.5rem; display: flex; flex-wrap: wrap; gap: 0.4rem; }
.draft-ban-chip {
    font-size: 0.72rem; font-weight: 600; color: #9CA3AF;
    background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.18);
    padding: 2px 9px; border-radius: 5px;
}
.draft-no-bans { font-size: 0.75rem; color: #6B7280; font-style: italic; }
.draft-timer-bar {
    display: flex; align-items: center; gap: 1rem;
    background: #0E1525; border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px; padding: 0.7rem 1.1rem; margin-bottom: 1rem;
}
.draft-timer-phase { font-size: 0.72rem; font-weight: 700;
    letter-spacing: 0.12em; text-transform: uppercase; color: #6B7280; }
.draft-timer-sec   { font-size: 1.4rem; font-weight: 900; color: #FFFFFF; min-width: 52px; }
.draft-timer-sec.urgent { color: #EF4444; }
.draft-waiting { text-align: center; padding: 3rem 1rem; color: #6B7280; }
.draft-waiting-icon  { font-size: 2.5rem; margin-bottom: 1rem; }
.draft-waiting-title { font-size: 1rem; font-weight: 700; color: #9CA3AF; margin-bottom: 0.4rem; }
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
.di-score-total    { font-size: 0.75rem; color: #6B7280; }
.di-score-label    { font-size: 0.62rem; font-weight: 700; letter-spacing: 0.14em;
    text-transform: uppercase; color: #9CA3AF; }
.di-factor-row {
    display: flex; align-items: center; gap: 0.6rem;
    margin-bottom: 0.45rem; font-size: 0.75rem;
}
.di-factor-label { color: #9CA3AF; min-width: 90px; }
.di-factor-bar-wrap {
    flex: 1; height: 5px; background: rgba(255,255,255,0.05);
    border-radius: 3px; overflow: hidden;
}
.di-factor-bar-fill { height: 100%; border-radius: 3px; }
.di-factor-pts { color: #6B7280; min-width: 40px; text-align: right; }

.di-rec-row {
    display: flex; align-items: center; gap: 0.65rem;
    padding: 0.65rem 0.9rem; border-radius: 8px; margin-bottom: 0.4rem;
    background: #0E1525; border: 1px solid rgba(255,255,255,0.04);
}
.di-rec-rank  { font-size: 0.78rem; font-weight: 900; color: #6B7280; min-width: 18px; }
.di-rec-champ { font-size: 0.9rem; font-weight: 800; color: #FFFFFF; flex: 1.2; }
.di-rec-stats { font-size: 0.75rem; color: #9CA3AF; flex: 1.8; }
.di-rec-tag   {
    font-size: 0.56rem; font-weight: 700; letter-spacing: 0.14em;
    text-transform: uppercase; padding: 2px 7px; border-radius: 4px;
}
.di-rec-tag.CARRY   { color: #22C55E; background: rgba(34,197,94,0.1); }
.di-rec-tag.COMFORT { color: #3B82F6; background: rgba(59,130,246,0.1); }
.di-rec-tag.MAIN    { color: #8B5CF6; background: rgba(139,92,246,0.1); }
.di-rec-tag.SOLID   { color: #F59E0B; background: rgba(245,158,11,0.1); }
.di-rec-conf { font-size: 0.7rem; color: #6B7280; min-width: 54px; text-align: right; }

.di-avoid-row {
    display: flex; align-items: center; gap: 0.65rem;
    padding: 0.55rem 0.9rem; border-radius: 8px; margin-bottom: 0.35rem;
    background: rgba(239,68,68,0.04); border: 1px solid rgba(239,68,68,0.12);
}
.di-avoid-champ { font-size: 0.87rem; font-weight: 700; color: #EF4444; flex: 1; }
.di-avoid-stats { font-size: 0.75rem; color: #9CA3AF; }

/* ── Draft Intelligence v2 — tarjeta con contexto ── */
.di-rec-v2 {
    background: #0E1525; border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px; padding: 0.85rem 1rem; margin-bottom: 0.6rem;
}
.di-v2-header {
    display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.7rem;
}
.di-v2-rank  { font-size: 0.85rem; font-weight: 900; color: #6B7280; min-width: 20px; }
.di-v2-champ { font-size: 0.97rem; font-weight: 800; color: #FFFFFF; flex: 1; }
.di-v2-scores {
    display: flex; align-items: center; gap: 1.25rem; margin-bottom: 0.65rem;
}
.di-v2-main {
    display: flex; flex-direction: column; align-items: center; gap: 1px;
    min-width: 52px;
}
.di-v2-ds     { font-size: 1.8rem; font-weight: 900; color: #8B5CF6; line-height: 1; }
.di-v2-ds-lbl { font-size: 0.56rem; color: #6B7280; text-transform: uppercase;
    letter-spacing: 0.1em; white-space: nowrap; }
.di-v2-breakdown { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.25rem 1rem; flex: 1; }
.di-v2-row  { display: flex; align-items: center; justify-content: space-between; }
.di-v2-lbl  { font-size: 0.68rem; color: #6B7280; }
.di-v2-val  { font-size: 0.78rem; font-weight: 700; }
.di-v2-reasons { display: flex; flex-direction: column; gap: 3px; }
.di-reason-pos { font-size: 0.71rem; color: #22C55E; }
.di-reason-neg { font-size: 0.71rem; color: #F59E0B; }

.di-warn-row {
    display: flex; gap: 0.6rem; align-items: flex-start;
    padding: 0.55rem 0.85rem; border-radius: 8px; margin-bottom: 0.4rem;
    font-size: 0.78rem; line-height: 1.5;
}
.di-warn-row.critical { background: rgba(239,68,68,0.07); border: 1px solid rgba(239,68,68,0.18); }
.di-warn-row.warning  { background: rgba(245,158,11,0.06); border: 1px solid rgba(245,158,11,0.15); }
.di-warn-row.info     { background: rgba(59,130,246,0.05); border: 1px solid rgba(59,130,246,0.12); }
.di-warn-icon { min-width: 18px; }
.di-warn-text { color: #9CA3AF; }

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
.ci-grade-score  { font-size: 0.78rem; color: #6B7280; margin-top: 2px; }
.ci-grade-desc   { font-size: 0.8rem; color: #9CA3AF; line-height: 1.5; }

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
.ci-class-meta { font-size: 0.7rem; color: #6B7280; }

.ci-champ-row {
    display: flex; align-items: center; gap: 0;
    padding: 0.6rem 0; border-bottom: 1px solid rgba(255,255,255,0.04);
}
.ci-champ-row:last-child { border-bottom: none; }
.ci-champ-name { font-size: 0.85rem; font-weight: 700; color: #D1D5DB; flex: 1.4; }
.ci-champ-games{ font-size: 0.78rem; color: #6B7280; flex: 0.6; }
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
.ci-insight-text { color: #9CA3AF; }

/* ═══════════════════════════════════════════════
   HERO — Coaching top section
═══════════════════════════════════════════════ */
.hero-card {
    background: #0E1525; border: 1px solid rgba(255,255,255,0.07);
    border-radius: 12px; padding: 1.4rem 1.75rem;
    display: flex; align-items: center; gap: 2rem;
    margin-bottom: 1.25rem;
}
.hero-score-block { display: flex; align-items: baseline; gap: 0.25rem; flex-shrink: 0; }
.hero-score       { font-size: 3.2rem; font-weight: 900; line-height: 1; }
.hero-score-denom { font-size: 1.1rem; font-weight: 400; color: #4B5563; align-self: flex-end; margin-bottom: 3px; }
.hero-label       { font-size: 0.72rem; font-weight: 700; letter-spacing: 0.12em;
    text-transform: uppercase; margin-left: 0.75rem; align-self: center; }
.hero-divider     { width: 1px; height: 52px; background: rgba(255,255,255,0.07); flex-shrink: 0; }
.hero-stats       { display: flex; gap: 2.25rem; flex: 1; }
.hero-stat        { display: flex; flex-direction: column; gap: 3px; }
.hero-stat-val    { font-size: 1.35rem; font-weight: 800; color: #FFFFFF; line-height: 1; }
.hero-stat-lbl    { font-size: 0.62rem; color: #6B7280; text-transform: uppercase; letter-spacing: 0.1em; }
.hero-stat-conf   { font-size: 0.82rem !important; }

/* ── Compact fortalezas / debilidades ── */
.compact-card   { padding: 1rem 1.1rem !important; }
.compact-item   {
    display: flex; align-items: flex-start; gap: 0.6rem;
    padding: 0.35rem 0; border-bottom: 1px solid rgba(255,255,255,0.04);
    line-height: 1.4;
}
.compact-item:last-child { border-bottom: none; }
.compact-icon-pos { color: #22C55E; font-size: 0.78rem; font-weight: 700; flex-shrink: 0; padding-top: 1px; }
.compact-icon-neg { color: #F59E0B; font-size: 0.78rem; font-weight: 700; flex-shrink: 0; padding-top: 1px; }
.compact-text     { font-size: 0.8rem; color: #9CA3AF; }
.compact-empty    { font-size: 0.78rem; color: #6B7280; padding: 0.25rem 0; }

/* ── Objetivo semanal rediseño ── */
.goal-metrics {
    display: flex; align-items: center; gap: 1rem; margin: 0.75rem 0 0.85rem;
}
.goal-metric        { text-align: center; }
.goal-metric-val    { font-size: 1.5rem; font-weight: 800; color: #FFFFFF; line-height: 1; }
.goal-metric-lbl    { font-size: 0.6rem; color: #6B7280; text-transform: uppercase;
    letter-spacing: 0.1em; margin-top: 3px; }
.goal-metric-arrow  { font-size: 1.1rem; color: #4B5563; padding-bottom: 12px; }
.goal-problem       { font-size: 0.78rem; font-weight: 700; color: #D1D5DB;
    letter-spacing: 0.06em; text-transform: uppercase; margin: 0.1rem 0 0.5rem; }
.goal-window        { font-size: 0.72rem; color: #6B7280; margin-top: 0.5rem; }

/* Sidebar: Config secundario */
[data-testid="stSidebar"] .stRadio > div > label:last-child {
    opacity: 0.65 !important;
    font-size: 0.78rem !important;
    font-weight: 400 !important;
}

/* ═══════════════════════════════════════════════
   ONBOARDING
═══════════════════════════════════════════════ */
.ob-logo {
    text-align: center; margin-bottom: 2rem;
}
.ob-logo-icon {
    width: 52px; height: 52px;
    background: linear-gradient(135deg,#8B5CF6,#6D28D9);
    border-radius: 14px;
    display: flex; align-items: center; justify-content: center;
    font-size: 1.6rem; margin: 0 auto 0.85rem;
}
.ob-logo-title { font-size: 1.15rem; font-weight: 800; color: #FFFFFF; letter-spacing: 0.05em; }
.ob-logo-sub   { font-size: 0.75rem; color: #6B7280; margin-top: 0.3rem; letter-spacing: 0.1em; text-transform: uppercase; }

/* Step bar */
.ob-steps {
    display: flex; align-items: flex-start; gap: 0;
    margin-bottom: 2rem; position: relative;
}
.ob-step {
    flex: 1; display: flex; flex-direction: column; align-items: center; gap: 7px;
    position: relative;
}
.ob-step:not(:last-child)::after {
    content: ''; position: absolute; top: 13px; left: calc(50% + 14px);
    right: calc(-50% + 14px); height: 1px;
    background: rgba(255,255,255,0.08);
}
.ob-step.done:not(:last-child)::after { background: rgba(139,92,246,0.35); }
.ob-step-dot {
    width: 28px; height: 28px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.72rem; font-weight: 700; z-index: 1;
    border: 1.5px solid rgba(255,255,255,0.1);
    background: #0A0F1E; color: #6B7280; flex-shrink: 0;
}
.ob-step.done   .ob-step-dot { background: #8B5CF6; border-color: #8B5CF6; color: #FFFFFF; font-size: 0.8rem; }
.ob-step.active .ob-step-dot { background: #0A0F1E; border-color: #8B5CF6; color: #8B5CF6; }
.ob-step-label { font-size: 0.63rem; color: #6B7280; text-align: center; line-height: 1.3; }
.ob-step.done   .ob-step-label { color: #8B5CF6; }
.ob-step.active .ob-step-label { color: #D1D5DB; }

/* Card de onboarding */
.ob-card {
    background: #0E1525; border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px; padding: 2rem 2rem 1.75rem;
    margin-bottom: 1rem;
}
.ob-card-title { font-size: 1.05rem; font-weight: 700; color: #FFFFFF; margin-bottom: 0.4rem; }
.ob-card-sub   { font-size: 0.84rem; color: #6B7280; margin-bottom: 1.75rem; line-height: 1.6; }

/* Account preview */
.ob-account-preview {
    background: rgba(139,92,246,0.07); border: 1px solid rgba(139,92,246,0.18);
    border-radius: 10px; padding: 0.9rem 1.1rem; margin-bottom: 1.5rem;
    display: flex; align-items: center; gap: 0.9rem;
}
.ob-account-icon  { font-size: 1.4rem; flex-shrink: 0; }
.ob-account-name  { font-size: 0.95rem; font-weight: 700; color: #FFFFFF; }
.ob-account-meta  { font-size: 0.75rem; color: #9CA3AF; margin-top: 2px; }
.ob-account-rank  { margin-left: auto; font-size: 0.82rem; font-weight: 700; color: #8B5CF6; white-space: nowrap; }

/* Inline feedback */
.ob-success {
    background: rgba(34,197,94,0.07); border: 1px solid rgba(34,197,94,0.18);
    border-radius: 8px; padding: 0.65rem 0.9rem; margin-bottom: 1.25rem;
    font-size: 0.83rem; color: #22C55E; display: flex; gap: 0.5rem; align-items: center;
}
.ob-error {
    background: rgba(239,68,68,0.07); border: 1px solid rgba(239,68,68,0.18);
    border-radius: 8px; padding: 0.65rem 0.9rem; margin-top: 0.75rem;
    font-size: 0.83rem; color: #EF4444; display: flex; gap: 0.5rem; align-items: center;
}

/* ═══════════════════════════════════════════════
   CONFIG PAGE
═══════════════════════════════════════════════ */
.cfg-stat-row {
    display: flex; gap: 1rem; margin-top: 0.75rem; flex-wrap: wrap;
}
.cfg-stat {
    flex: 1; min-width: 80px;
    background: #0E1525; border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px; padding: 0.9rem 1rem;
}
.cfg-stat-val { font-size: 1.5rem; font-weight: 800; color: #FFFFFF; }
.cfg-stat-lbl { font-size: 0.68rem; color: #6B7280; margin-top: 2px;
    letter-spacing: 0.08em; text-transform: uppercase; }
.cfg-stat-sub { font-size: 0.72rem; color: #4B5563; margin-top: 1px; }

/* ═══════════════════════════════════════════════
   SYNC STATUS (sidebar)
═══════════════════════════════════════════════ */
.sb-sync-status {
    display: flex; align-items: center; gap: 6px;
    padding: 0.45rem 0.5rem 0;
    font-size: 0.68rem; color: #6B7280;
}
.sb-sync-dot {
    width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0;
}
.sb-sync-dot.ok    { background: #22C55E; }
.sb-sync-dot.warn  { background: #F59E0B; }
.sb-sync-dot.error { background: #EF4444; }
</style>
"""


# is_setup_complete() importada desde backend.services.setup_service


# ---------------------------------------------------------------------------
# Sync automático
# ---------------------------------------------------------------------------

def _maybe_sync() -> None:
    """
    Ejecuta sync incremental si han pasado más de SYNC_INTERVAL_MINUTES
    desde la última sync.  Usa session_state para no re-verificar en
    cada rerun dentro del mismo intervalo.
    """
    from datetime import datetime

    now        = datetime.now()
    last_check = st.session_state.get("_sync_last_checked")

    # Evitar chequeo redundante en reruns normales (clics, selectboxes, etc.)
    interval_sec = sync_service.SYNC_INTERVAL_MINUTES * 60
    if last_check and (now - last_check).total_seconds() < interval_sec:
        return

    if not sync_service.should_sync():
        st.session_state["_sync_last_checked"] = now
        return

    # Necesitamos sync: ejecutar con spinner transparente
    with st.spinner("🔄 Sincronizando partidas..."):
        result = sync_service.sync_matches()

    st.session_state["_sync_last_checked"] = now

    if result.saved > 0:
        sync_service.invalidate_caches(st.session_state)
        st.toast(f"✅ {result.saved} partidas nuevas sincronizadas", icon="✅")
    elif result.status == "rate_limited":
        st.toast("⏳ Rate limit alcanzado. Usando datos locales.", icon="⏳")
    elif result.status == "error" and result.error_msg:
        st.toast(f"⚠️ Sync: {result.error_msg[:60]}", icon="⚠️")


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

    # ----------------------------------------------------------------
    # Gate de acceso — debe ejecutarse ANTES de renderizar cualquier cosa
    # ----------------------------------------------------------------
    if not is_setup_complete():
        page_onboarding.render()
        st.stop()

    # ----------------------------------------------------------------
    # Sync automático (incremental, solo si han pasado > 15 min)
    # ----------------------------------------------------------------
    _maybe_sync()

    # ----------------------------------------------------------------
    # Sidebar — solo se construye cuando el setup está completo
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

        page = st.radio(
            "nav",
            options=["🧠 Coaching", "🎮 Partidas", "🎯 Draft", "⚙️ Configuración"],
            label_visibility="collapsed",
            key="current_page",
        )

        puuid  = db.get_config("puuid")
        player = db.get_player(puuid) if puuid else None
        if player:
            sync_label = sync_service.sync_status_label()
            sync_min   = sync_service.minutes_since_last_sync()
            sync_dot_class = (
                "ok"   if sync_min < 60   else
                "warn" if sync_min < 1440 else
                "error"
            )
            st.markdown(
                f'<div class="sb-player-card">'
                f'<div class="sb-player-name">👤 {player["riot_id"]}#{player["tag"]}</div>'
                f'<div class="sb-player-level">Nivel {player.get("level", "?")}</div>'
                f'<div class="sb-player-rank">{player.get("rank", "Sin rango")} · {player.get("lp", 0)} LP</div>'
                f'</div>'
                f'<div class="sb-sync-status">'
                f'<div class="sb-sync-dot {sync_dot_class}"></div>'
                f'<span>{sync_label}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

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
