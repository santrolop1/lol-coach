"""
ui/coaching.py — Página principal de coaching personalizado.

Conecta scorer_v2 + coaching_engine con la interfaz premium.
Roles soportados: ADC, TOP.
"""

import sys
import statistics
import dataclasses
from pathlib import Path
from datetime import datetime, timezone

import streamlit as st
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).parent.parent))

import db
import scorer_v2
import coaching_engine
import coaching_rules
from backend.services.matchup_models import MatchupResult, MatchupRecord
from backend.services.champion_models import ChampionCoachResult
from backend.services.post_game_review import generate_review
from backend.services.review_models import PostGameReview
from backend.services.priority_engine import Priority
from backend.viewmodels.coaching_vm import build_coaching, build_champion_coach


# ---------------------------------------------------------------------------
# Helpers de UI
# ---------------------------------------------------------------------------

def _tier(score: float) -> tuple[str, str]:
    """Devuelve (label, color) según el score overall."""
    if score >= 80: return "EXCELENTE", "#22C55E"
    if score >= 65: return "BUENO",     "#8B5CF6"
    if score >= 50: return "EN PROGRESO","#3B82F6"
    if score >= 35: return "A MEJORAR", "#F59E0B"
    return "CRÍTICO", "#EF4444"


def _problem_icon(name: str) -> str:
    n = name.lower()
    if "muerte" in n or "morir" in n:    return "💀"
    if "tilt" in n or "racha" in n:      return "⚡"
    if "cs" in n or "farm" in n or "línea" in n or "linea" in n: return "🌾"
    if "objetivo" in n:                  return "🎯"
    if "participaci" in n:               return "👥"
    if "inconsist" in n:                 return "📊"
    if "presión" in n or "presion" in n or "torre" in n: return "🏯"
    if "ventaja" in n or "conversión" in n: return "⚔️"
    return "⚠️"


def _sec_icon(idx: int) -> str:
    return ["👁️", "🏃", "💰", "📍", "⚔️"][idx % 5]


def _goal_progress_pct(current: float, target: float, metric: str) -> float:
    """Porcentaje visual de progreso hacia el objetivo (0-95)."""
    lower_is_better = metric in ("deaths", "cs_at_10")
    if lower_is_better:
        if current <= target:
            return 95.0
        bad = max(current * 1.5, target + 4)
        pct = (bad - current) / max(bad - target, 0.01) * 100
    else:
        if current >= target:
            return 95.0
        bad = min(current * 0.5, target - 0.2)
        pct = (current - bad) / max(target - bad, 0.01) * 100
    return max(5.0, min(95.0, pct))


def _avg(vals: list) -> float:
    return statistics.mean(vals) if vals else 0.0


def _safe(match: dict, key: str):
    v = match.get(key)
    return float(v) if v is not None else None


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def _ring_chart(score: float, color: str) -> go.Figure:
    fig = go.Figure(go.Pie(
        values=[score, 100 - score],
        hole=0.76,
        marker=dict(colors=[color, "#111827"], line=dict(width=0)),
        showlegend=False, textinfo="none", hoverinfo="none",
        direction="clockwise", rotation=90,
    ))
    fig.update_layout(
        width=170, height=170,
        margin=dict(l=5, r=5, t=5, b=5),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        annotations=[dict(
            text=f"<b>{score:.0f}</b>",
            x=0.5, y=0.5,
            font=dict(size=34, color="#FFFFFF", family="Arial Black"),
            showarrow=False,
        )],
    )
    return fig


def _sparkline(match_scores: list) -> go.Figure:
    scores = [ms.overall_score for ms in reversed(match_scores) if ms.overall_score is not None]
    if not scores:
        return go.Figure()
    n = len(scores)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(range(n)), y=scores,
        fill="tozeroy", fillcolor="rgba(139,92,246,0.06)",
        line=dict(color="rgba(0,0,0,0)"),
        showlegend=False, hoverinfo="none",
    ))
    fig.add_trace(go.Scatter(
        x=list(range(n)), y=scores,
        mode="lines+markers",
        line=dict(color="#8B5CF6", width=2.5, shape="spline", smoothing=0.5),
        marker=dict(color="#8B5CF6", size=4),
        showlegend=False,
        hovertemplate="%{y:.0f}<extra></extra>",
    ))
    fig.update_layout(
        height=100, margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, zeroline=False, range=[0, 105]),
        showlegend=False,
    )
    return fig


def _deaths_chart(matches: list[dict], match_scores: list) -> go.Figure:
    """Gráfica de muertes por partida, orden cronológico, coloreada por resultado."""
    items = [
        (m.get("deaths", 0), ms.result)
        for m, ms in zip(reversed(matches), reversed(match_scores))
        if ms.overall_score is not None
    ]
    if not items:
        return go.Figure()
    deaths, results = zip(*items)
    n = len(deaths)
    x = list(range(n))
    colors = ["#22C55E" if r == "WIN" else "#EF4444" for r in results]
    step = max(1, n // 6)
    tvals = list(range(0, n, step))
    if n - 1 not in tvals:
        tvals.append(n - 1)
    ttext = [f"H-{n-1-i}" if i < n - 1 else "HOY" for i in tvals]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=list(deaths),
        mode="lines+markers",
        line=dict(color="#F59E0B", width=2.5, shape="spline", smoothing=0.4),
        marker=dict(color=colors, size=7, line=dict(color="#0A0F1E", width=2)),
        showlegend=False,
        hovertemplate="Muertes: %{y}<extra></extra>",
    ))
    fig.update_layout(
        height=120, margin=dict(l=0, r=10, t=5, b=25),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            showgrid=False, zeroline=False,
            tickvals=tvals, ticktext=ttext,
            tickfont=dict(color="#6B7280", size=10), showline=False,
        ),
        yaxis=dict(
            showgrid=True, gridcolor="rgba(255,255,255,0.03)",
            zeroline=False, tickfont=dict(color="#6B7280", size=10),
            range=[0, max(max(deaths) + 2, 8)],
        ),
        showlegend=False, hovermode="x unified",
    )
    return fig


def _trend_chart(match_scores: list) -> go.Figure:
    items = [
        (ms.played_at[:10] if ms.played_at else "", ms.overall_score, ms.result)
        for ms in reversed(match_scores)
        if ms.overall_score is not None
    ]
    if not items:
        return go.Figure()
    dates, scores, results = zip(*items)
    n = len(scores)
    x = list(range(n))
    colors = ["#22C55E" if r == "WIN" else "#EF4444" for r in results]
    # X-axis labels
    step = max(1, n // 6)
    tvals = list(range(0, n, step))
    if n - 1 not in tvals:
        tvals.append(n - 1)
    ttext = [f"H-{n-1-i}" if i < n - 1 else "HOY" for i in tvals]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x, y=list(scores),
        fill="tozeroy", fillcolor="rgba(139,92,246,0.04)",
        line=dict(color="rgba(0,0,0,0)"),
        showlegend=False, hoverinfo="none",
    ))
    fig.add_trace(go.Scatter(
        x=x, y=list(scores),
        mode="lines+markers",
        line=dict(color="#8B5CF6", width=2.5, shape="spline", smoothing=0.4),
        marker=dict(color=colors, size=7, line=dict(color="#0A0F1E", width=2)),
        showlegend=False,
        hovertemplate="Score: %{y:.0f}<extra></extra>",
    ))
    fig.update_layout(
        height=150, margin=dict(l=0, r=10, t=5, b=25),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            showgrid=False, zeroline=False,
            tickvals=tvals, ticktext=ttext,
            tickfont=dict(color="#6B7280", size=10), showline=False,
        ),
        yaxis=dict(
            showgrid=True, gridcolor="rgba(255,255,255,0.03)",
            zeroline=False, tickfont=dict(color="#6B7280", size=10), range=[0, 105],
        ),
        showlegend=False, hovermode="x unified",
    )
    return fig


# ---------------------------------------------------------------------------
# Cómputo de métricas desde partidas crudas
# ---------------------------------------------------------------------------


def _problem_stats(cr, mx: dict) -> tuple:
    """
    Devuelve (main_val_str, main_label, win_val_str, loss_val_str)
    según el primary problem.
    """
    goal = cr.weekly_goal
    metric = goal.metric if goal else "deaths"

    if metric == "deaths":
        main = f"{mx['deaths']:.1f}" if mx.get("deaths") else "—"
        lbl  = "Muertes / partida"
        wv   = f"{mx['deaths_win']:.1f}" if mx.get("deaths_win") else "—"
        lv   = f"{mx['deaths_loss']:.1f}" if mx.get("deaths_loss") else "—"
    elif metric == "kill_participation":
        main = f"{mx['kp']:.0%}" if mx.get("kp") else "—"
        lbl  = "KP promedio"
        wv   = f"{mx['kp_win']:.0%}" if mx.get("kp_win") else "—"
        lv   = f"{mx['kp_loss']:.0%}" if mx.get("kp_loss") else "—"
    elif metric in ("cs_at_10", "turret_takedowns", "consistency_score", "objective_damage_per_min"):
        main = f"{goal.current:.1f}" if goal else "—"
        lbl  = "Valor actual"
        wv   = "—"
        lv   = "—"
    else:
        main = f"{goal.current:.1f}" if goal else "—"
        lbl  = "Valor actual"
        wv   = "—"
        lv   = "—"

    return main, lbl, wv, lv


def _impact_for(display_name: str, role: str) -> str:
    """Devuelve el texto de impacto real desde coaching_rules para un display_name dado."""
    problem_map = (
        coaching_rules.ADC_PROBLEMS if role == "ADC" else coaching_rules.TOP_PROBLEMS
    )
    for rule in problem_map.values():
        if rule.get("display_name") == display_name:
            return rule.get("impact", "")
    return ""


def _format_goal_value(val: float, metric: str) -> str:
    if metric == "kill_participation":
        return f"{val:.0%}"
    if metric in ("cs_at_10", "turret_takedowns"):
        return f"{val:.0f}"
    return f"{val:.1f}"


# ---------------------------------------------------------------------------
# Secciones de render
# ---------------------------------------------------------------------------

def _render_session_alert(warning: str) -> None:
    if not warning:
        return
    st.markdown(
        f'<div class="session-alert">'
        f'<div class="session-alert-icon">⚡</div>'
        f'<div>'
        f'<div class="session-alert-title">ALERTA DE SESIÓN</div>'
        f'<div class="session-alert-body">{warning}</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def _render_priorities(priorities: list[Priority]) -> None:
    """Sección 🎯 MAYOR GANANCIA POTENCIAL — máximo 3 prioridades."""
    if not priorities:
        return

    top3 = priorities[:3]

    conf_badge = {
        "medium": '<span class="prio-conf medium">preliminar</span>',
        "high":   '<span class="prio-conf high">confiable</span>',
    }

    items_html = ""
    for i, p in enumerate(top3, start=1):
        bar_w   = round(p.impact_score / 20 * 100)
        badge   = conf_badge.get(p.confidence, "")
        items_html += (
            f'<div class="prio-row">'
            f'  <div class="prio-rank">#{i}</div>'
            f'  <div class="prio-body">'
            f'    <div class="prio-header">'
            f'      <div class="prio-title">{p.title}</div>'
            f'      <div class="prio-impact">+{p.impact_score} <span class="prio-impact-lbl">impacto</span></div>'
            f'    </div>'
            f'    <div class="prio-bar-track"><div class="prio-bar-fill" style="width:{bar_w}%"></div></div>'
            f'    <div class="prio-evidence">{p.evidence}</div>'
            f'    <div class="prio-rec">→ {p.recommendation} {badge}</div>'
            f'  </div>'
            f'</div>'
        )

    st.markdown(
        f'<div class="prio-card">'
        f'<div class="card-label">🎯 &nbsp;MAYOR GANANCIA POTENCIAL</div>'
        f'{items_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_hero(sr, mx: dict, cr) -> None:
    """Hero section: score + contexto en una sola fila compacta."""
    score        = sr.overall_score or 50.0
    label, color = _tier(score)

    n_wins = mx.get("n_wins", 0)
    n_tot  = mx.get("n", 1)
    wr     = n_wins / n_tot * 100 if n_tot else 0

    # Tendencia numérica
    all_sc = [ms.overall_score for ms in sr.match_scores if ms.overall_score is not None]
    trend_str   = "—"
    trend_color = "#6B7280"
    if len(all_sc) >= 6:
        mid   = len(all_sc) // 2
        delta = _avg(all_sc[:mid]) - _avg(all_sc[mid:])
        sign  = "+" if delta >= 0 else ""
        trend_str   = f"{sign}{delta:.0f}"
        trend_color = "#22C55E" if delta >= 0 else "#EF4444"

    conf_labels = {
        "insufficient": "⚠️ Insuficiente",
        "preliminary":  "📊 Preliminar",
        "reliable":     "✅ Confiable",
        "robust":       "✅ Robusto",
    }
    conf_text = conf_labels.get(cr.confidence_level, cr.confidence_level)

    st.markdown(
        f'<div class="hero-card">'
        f'  <div class="hero-score-block">'
        f'    <div class="hero-score" style="color:{color}">{score:.0f}</div>'
        f'    <div class="hero-score-denom">/100</div>'
        f'    <div class="hero-label" style="color:{color}">{label}</div>'
        f'  </div>'
        f'  <div class="hero-divider"></div>'
        f'  <div class="hero-stats">'
        f'    <div class="hero-stat"><div class="hero-stat-val">{wr:.0f}%</div><div class="hero-stat-lbl">Winrate</div></div>'
        f'    <div class="hero-stat"><div class="hero-stat-val">{n_wins}/{n_tot}</div><div class="hero-stat-lbl">V / P</div></div>'
        f'    <div class="hero-stat"><div class="hero-stat-val" style="color:{trend_color}">{trend_str}</div><div class="hero-stat-lbl">Tendencia</div></div>'
        f'    <div class="hero-stat"><div class="hero-stat-val hero-stat-conf">{conf_text}</div><div class="hero-stat-lbl">Análisis</div></div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_objetivo(cr) -> None:
    goal = cr.weekly_goal
    if not goal:
        return
    metric  = goal.metric
    cur_str = _format_goal_value(goal.current, metric)
    tgt_str = _format_goal_value(goal.target,  metric)
    pct     = _goal_progress_pct(goal.current, goal.target, metric)

    lower_is_better = metric in ("deaths", "cs_at_10")
    raw_diff  = goal.target - goal.current
    diff_good = (raw_diff < 0) if lower_is_better else (raw_diff > 0)
    sign      = "+" if raw_diff >= 0 else ""
    diff_str  = f"{sign}{_format_goal_value(abs(raw_diff), metric)}"
    diff_color = "#22C55E" if diff_good else "#EF4444"

    st.markdown(
        f'<div class="goal-card">'
        f'  <div class="card-label">🎯 &nbsp;OBJETIVO SEMANAL</div>'
        f'  <div class="goal-problem">{cr.primary_problem.upper()}</div>'
        f'  <div class="goal-metrics">'
        f'    <div class="goal-metric"><div class="goal-metric-val">{cur_str}</div><div class="goal-metric-lbl">Actual</div></div>'
        f'    <div class="goal-metric-arrow">→</div>'
        f'    <div class="goal-metric"><div class="goal-metric-val">{tgt_str}</div><div class="goal-metric-lbl">Objetivo</div></div>'
        f'    <div class="goal-metric"><div class="goal-metric-val" style="color:{diff_color}">{diff_str}</div><div class="goal-metric-lbl">Diferencia</div></div>'
        f'  </div>'
        f'  <div class="goal-bar-track"><div class="goal-bar-fill" style="width:{pct:.0f}%"></div></div>'
        f'  <div class="goal-window">Ventana: {goal.window}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_problema(cr, mx: dict) -> None:
    icon = _problem_icon(cr.primary_problem)
    main_val, main_lbl, win_val, loss_val = _problem_stats(cr, mx)
    show_cmp = win_val != "—" and loss_val != "—"

    cmp_html = ""
    if show_cmp:
        cmp_html = (
            f'<div class="problem-cmp">'
            f'<div class="problem-cmp-col">'
            f'<div class="problem-cmp-val-w">{win_val}</div>'
            f'<div class="problem-cmp-lbl">En victorias</div></div>'
            f'<div class="problem-cmp-col">'
            f'<div class="problem-cmp-val-l">{loss_val}</div>'
            f'<div class="problem-cmp-lbl">En derrotas</div></div>'
            f'</div>'
        )

    st.markdown(
        f'<div class="problem-card">'
        f'<div style="display:flex;align-items:flex-start;justify-content:space-between">'
        f'<div class="problem-label">⚠️ &nbsp;TU PROBLEMA PRINCIPAL</div>'
        f'<div style="font-size:2rem;opacity:0.35">{icon}</div>'
        f'</div>'
        f'<div class="problem-title">{cr.primary_problem.upper()}</div>'
        f'<div class="problem-main-stat">{main_val}</div>'
        f'<div class="problem-main-sub">{main_lbl}</div>'
        f'{cmp_html}'
        f'<div class="problem-desc">{cr.probable_cause}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def _render_plan(cr) -> None:
    icon = _problem_icon(cr.primary_problem)
    sec_items = "".join(
        f'<div class="plan-sec-item">'
        f'<span class="plan-sec-icon">{_sec_icon(i)}</span>'
        f'<span>{action}</span></div>'
        for i, action in enumerate(cr.training_plan.secondary)
    )
    st.markdown(
        f'<div class="plan-card">'
        f'<div class="card-label">🎓 &nbsp;TU PLAN DE ENTRENAMIENTO</div>'
        f'<div class="plan-main">'
        f'<div class="plan-icon-box">{icon}</div>'
        f'<div>'
        f'<div class="plan-action-lbl">ACCIÓN PRINCIPAL</div>'
        f'<div class="plan-action-text">{cr.training_plan.primary}</div>'
        f'</div></div>'
        f'<div class="plan-sec">'
        f'<div class="plan-sec-lbl">ENFOQUE SECUNDARIO</div>'
        f'{sec_items}'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def _render_strengths_weaknesses(cr, role: str) -> None:
    col_s, col_w = st.columns(2, gap="medium")

    with col_s:
        st.markdown(
            '<div class="card compact-card">'
            '<div class="card-label">💪 &nbsp;FORTALEZAS</div>',
            unsafe_allow_html=True,
        )
        if cr.strengths:
            for s in cr.strengths:
                st.markdown(
                    f'<div class="compact-item">'
                    f'<span class="compact-icon-pos">✓</span>'
                    f'<span class="compact-text">{s.evidence}</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown('<div class="compact-empty">Sigue jugando para detectar fortalezas consistentes.</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_w:
        st.markdown(
            '<div class="card compact-card">'
            '<div class="card-label">⚠️ &nbsp;DEBILIDADES</div>',
            unsafe_allow_html=True,
        )
        items = [(cr.primary_problem, cr.impact)] + [
            (imp, _impact_for(imp, role) or "Área de mejora identificada en tu historial.")
            for imp in cr.improvements
        ]
        for _, evidence in items:
            st.markdown(
                f'<div class="compact-item">'
                f'<span class="compact-icon-neg">⚠</span>'
                f'<span class="compact-text">{evidence}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)


def _render_trend_chart(sr, mx: dict, matches: list[dict]) -> None:
    all_sc = [ms.overall_score for ms in sr.match_scores if ms.overall_score is not None]
    best  = max(all_sc) if all_sc else 0
    worst = min(all_sc) if all_sc else 0
    last_raw = sr.match_scores[0].overall_score if sr.match_scores else None
    last_str  = f"{last_raw:.0f}" if last_raw is not None else "—"
    best_str  = f"{best:.0f}"
    worst_str = f"{worst:.0f}"

    valid_pairs = [
        (m.get("deaths", 0), ms)
        for m, ms in zip(matches, sr.match_scores)
        if ms.overall_score is not None
    ]
    avg_deaths_str = f"{sum(d for d, _ in valid_pairs) / len(valid_pairs):.1f}" if valid_pairs else "—"
    best_deaths = min(d for d, _ in valid_pairs) if valid_pairs else 0
    worst_deaths = max(d for d, _ in valid_pairs) if valid_pairs else 0

    col_chart, col_stats = st.columns([3, 1], gap="medium")
    with col_chart:
        st.markdown(
            '<div class="card">'
            '<div class="card-label">📈 &nbsp;SCORE — EVOLUCIÓN</div>',
            unsafe_allow_html=True,
        )
        fig = _trend_chart(sr.match_scores)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown(
            '<div class="card" style="margin-top:0.75rem">'
            '<div class="card-label">💀 &nbsp;MUERTES — EVOLUCIÓN</div>',
            unsafe_allow_html=True,
        )
        fig_d = _deaths_chart(matches, sr.match_scores)
        st.plotly_chart(fig_d, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with col_stats:
        st.markdown(
            f'<div class="card" style="display:flex;flex-direction:column;gap:1.25rem">'
            f'<div class="card-label" style="margin-bottom:0.25rem">SCORE</div>'
            f'<div>'
            f'<div style="font-size:0.64rem;color:#6B7280;font-weight:700;letter-spacing:0.12em;text-transform:uppercase">Última</div>'
            f'<div style="font-size:1.8rem;font-weight:900;color:#8B5CF6;line-height:1">{last_str}</div>'
            f'</div>'
            f'<div>'
            f'<div style="font-size:0.64rem;color:#6B7280;font-weight:700;letter-spacing:0.12em;text-transform:uppercase">Mejor</div>'
            f'<div style="font-size:1.8rem;font-weight:900;color:#22C55E;line-height:1">{best_str}</div>'
            f'</div>'
            f'<div>'
            f'<div style="font-size:0.64rem;color:#6B7280;font-weight:700;letter-spacing:0.12em;text-transform:uppercase">Peor</div>'
            f'<div style="font-size:1.8rem;font-weight:900;color:#EF4444;line-height:1">{worst_str}</div>'
            f'</div>'
            f'<div style="border-top:1px solid rgba(255,255,255,0.05);padding-top:1rem;margin-top:0.5rem">'
            f'<div class="card-label" style="margin-bottom:0.25rem">MUERTES</div>'
            f'</div>'
            f'<div>'
            f'<div style="font-size:0.64rem;color:#6B7280;font-weight:700;letter-spacing:0.12em;text-transform:uppercase">Promedio</div>'
            f'<div style="font-size:1.8rem;font-weight:900;color:#F59E0B;line-height:1">{avg_deaths_str}</div>'
            f'</div>'
            f'<div>'
            f'<div style="font-size:0.64rem;color:#6B7280;font-weight:700;letter-spacing:0.12em;text-transform:uppercase">Mejor</div>'
            f'<div style="font-size:1.8rem;font-weight:900;color:#22C55E;line-height:1">{best_deaths}</div>'
            f'</div>'
            f'<div>'
            f'<div style="font-size:0.64rem;color:#6B7280;font-weight:700;letter-spacing:0.12em;text-transform:uppercase">Peor</div>'
            f'<div style="font-size:1.8rem;font-weight:900;color:#EF4444;line-height:1">{worst_deaths}</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


def _render_datos_avanzados(mx: dict, benchmarks, role: str) -> None:
    bm = benchmarks.metrics if benchmarks else {}

    def pct_from_bm(key: str, val: float | None) -> int | None:
        if val is None:
            return None
        stats = bm.get(key)
        if not stats:
            return None
        vals = [stats.p25, stats.p50, stats.p75]
        below = sum(1 for v in vals if val > v)
        return [25, 50, 75, 90][min(below, 3)]

    # Definir métricas según rol
    if role == "ADC":
        metrics = [
            ("CS / MIN",      mx.get("cs_pm"),     "cs_per_min",     "{:.1f}"),
            ("DAÑO / MIN",    mx.get("dmg_pm"),     "damage_per_min", "{:.0f}"),
            ("PARTICIPACIÓN", mx.get("kp"),         "kill_participation", "{:.0%}"),
            ("MUERTES",       mx.get("deaths"),     "deaths",         "{:.1f}"),
            ("VISIÓN / MIN",  mx.get("vision_pm"),  "vision_score_per_min", "{:.1f}"),
            ("ORO / MIN",     mx.get("gold_pm"),    "gold_per_min",   "{:.0f}"),
        ]
    else:
        metrics = [
            ("CS / MIN",      mx.get("cs_pm"),     "cs_per_min",     "{:.1f}"),
            ("DAÑO / MIN",    mx.get("dmg_pm"),     "damage_per_min", "{:.0f}"),
            ("MUERTES",       mx.get("deaths"),     "deaths",         "{:.1f}"),
            ("VISIÓN / MIN",  mx.get("vision_pm"),  "vision_score_per_min", "{:.1f}"),
            ("OBJ / MIN",     mx.get("obj_pm"),     "objective_damage_per_min", "{:.0f}"),
            ("ORO / MIN",     mx.get("gold_pm"),    "gold_per_min",   "{:.0f}"),
        ]

    cols = st.columns(len(metrics), gap="small")
    for col, (lbl, val, bm_key, fmt) in zip(cols, metrics):
        val_str = fmt.format(val) if val is not None else "—"
        pct     = pct_from_bm(bm_key, val)
        pct_str = f"P{pct}" if pct else "—"
        bar_pct = pct if pct else 0

        with col:
            st.markdown(
                f'<div class="metric-card">'
                f'<div class="metric-lbl">{lbl}</div>'
                f'<div class="metric-val">{val_str}</div>'
                f'<div class="metric-pct">{pct_str}</div>'
                f'<div class="metric-bar">'
                f'<div class="metric-bar-fill" style="width:{bar_pct}%"></div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )


def _render_match_summary(matches: list[dict], match_scores: list) -> None:
    rows = []
    for m, ms in zip(matches[:5], match_scores[:5]):
        score = ms.overall_score if ms.overall_score is not None else 0.0
        is_win = m.get("result") == "WIN"
        rows.append({
            "win": is_win,
            "result": "Victoria" if is_win else "Derrota",
            "champion": m.get("champion", "?"),
            "kda": f"{m.get('kills',0)}/{m.get('deaths',0)}/{m.get('assists',0)}",
            "date": (m.get("played_at") or "")[:10],
            "score": score,
        })

    items_html = ""
    for r in rows:
        sc_color = "#22C55E" if r["score"] >= 65 else ("#F59E0B" if r["score"] >= 40 else "#EF4444")
        res_cls = "result-win" if r["win"] else "result-loss"
        items_html += (
            f'<div class="match-row">'
            f'<div class="match-row-result {res_cls}">{r["result"]}</div>'
            f'<div class="match-row-info">'
            f'<div class="match-row-champ">{r["champion"]}</div>'
            f'<div class="match-row-kda">{r["kda"]} · {r["date"]}</div>'
            f'</div>'
            f'<div class="match-row-score" style="color:{sc_color}">{r["score"]:.0f}</div>'
            f'</div>'
        )

    st.markdown(
        f'<div class="card">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.85rem">'
        f'<div class="card-label" style="margin-bottom:0">RESUMEN DE PARTIDAS</div>'
        f'</div>'
        f'{items_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Champion Intelligence
# ---------------------------------------------------------------------------

def _grade_color(grade: str) -> str:
    return {"A": "#22C55E", "B": "#8B5CF6", "C": "#3B82F6", "D": "#F59E0B", "F": "#EF4444"}.get(grade, "#6B7280")


def _wr_color(wr: float) -> str:
    if wr >= 0.55: return "#22C55E"
    if wr >= 0.45: return "#F59E0B"
    return "#EF4444"


def _trend_icon(slope: float) -> str:
    if slope > 1.5:  return '<span style="color:#22C55E">↑</span>'
    if slope < -1.5: return '<span style="color:#EF4444">↓</span>'
    return '<span style="color:#6B7280">→</span>'


def _hex_to_rgb(hex_color: str) -> str:
    """Convierte '#RRGGBB' a 'R,G,B' para usar en rgba()."""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"{r},{g},{b}"


# ---------------------------------------------------------------------------
# Champion Coach
# ---------------------------------------------------------------------------

_CC_PRIORITY_LABELS = {
    "main":         ("MAIN",         "#8B5CF6"),
    "growth":       ("GROWTH PICK",  "#22C55E"),
    "risk":         ("RISK PICK",    "#EF4444"),
    "insufficient": ("SIN DATOS",    "#6B7280"),
}

_CC_TREND_LABELS = {
    "improving":    ("Mejorando",    "#22C55E"),
    "declining":    ("Decayendo",    "#EF4444"),
    "stable":       ("Estable",      "#F59E0B"),
    "insufficient": ("—",            "#6B7280"),
}

_CC_PATTERN_ICONS = {
    "deaths":      "💀",
    "farm":        "🌾",
    "damage":      "⚔️",
    "kp":          "👥",
    "consistency": "📊",
}


def _render_champion_coach(
    result: ChampionCoachResult,
    role: str,
) -> None:
    """Renderiza el panel completo de coaching para el campeón seleccionado."""
    a = result.analysis
    name = a.champion_name

    # ── Hero del campeón ──────────────────────────────────────────────────────
    prio_label, prio_color = _CC_PRIORITY_LABELS.get(result.priority_class, ("—", "#6B7280"))
    trend_label, trend_color = _CC_TREND_LABELS.get(a.trend, ("—", "#6B7280"))
    wr_color = _wr_color(a.winrate)
    conf_map = {"low": "⚠️ Preliminar", "medium": "📊 En progreso", "high": "✅ Confiable"}
    conf_str = conf_map.get(a.confidence, "—")
    score_str = f"{a.avg_score:.0f}" if a.avg_score is not None else "—"

    st.markdown(
        f'<div class="cc-hero">'
        f'  <div class="cc-hero-left">'
        f'    <div class="cc-champ-name">{name}</div>'
        f'    <div class="cc-prio-badge" style="background:rgba({_hex_to_rgb(prio_color)},0.15);'
        f'color:{prio_color}">{prio_label}</div>'
        f'  </div>'
        f'  <div class="cc-hero-stats">'
        f'    <div class="cc-hstat"><div class="cc-hstat-val">{a.games}</div><div class="cc-hstat-lbl">Partidas</div></div>'
        f'    <div class="cc-hstat"><div class="cc-hstat-val" style="color:{wr_color}">{a.winrate:.0%}</div><div class="cc-hstat-lbl">WR</div></div>'
        f'    <div class="cc-hstat"><div class="cc-hstat-val">{score_str}</div><div class="cc-hstat-lbl">Score</div></div>'
        f'    <div class="cc-hstat"><div class="cc-hstat-val" style="color:{trend_color}">{trend_label}</div><div class="cc-hstat-lbl">Tendencia</div></div>'
        f'    <div class="cc-hstat"><div class="cc-hstat-val cc-conf">{conf_str}</div><div class="cc-hstat-lbl">Análisis</div></div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Datos insuficientes ───────────────────────────────────────────────────
    from backend.config.constants import MIN_CHAMPION_GAMES
    if result.priority_class == "insufficient":
        st.markdown(
            f'<div class="card" style="color:#6B7280;font-size:0.82rem;padding:1rem 1.4rem">'
            f'Necesitas al menos {MIN_CHAMPION_GAMES} partidas con {name} para activar el Champion Coach. '
            f'Tienes {a.games} hasta ahora.'
            f'</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Problema principal + Objetivo ─────────────────────────────────────────
    col_prob, col_goal = st.columns([1, 1], gap="medium")

    with col_prob:
        if result.primary_problem:
            icon = "⚠️"
            first_pattern = result.patterns[0] if result.patterns else None
            desc = first_pattern.description if first_pattern else result.primary_problem
            sev_color = "#EF4444" if (first_pattern and first_pattern.severity == "critical") else "#F59E0B"
            st.markdown(
                f'<div class="card cc-prob-card">'
                f'<div class="card-label">⚠️ &nbsp;PROBLEMA PRINCIPAL</div>'
                f'<div class="cc-prob-title" style="color:{sev_color}">{result.primary_problem.upper()}</div>'
                f'<div class="cc-prob-desc">{desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="card cc-prob-card">'
                f'<div class="card-label">✅ &nbsp;SIN PROBLEMAS DETECTADOS</div>'
                f'<div class="cc-prob-desc" style="color:#22C55E">'
                f'No se detectaron patrones negativos con {name} en tus últimas {a.games} partidas.'
                f'</div></div>',
                unsafe_allow_html=True,
            )

    with col_goal:
        g = result.goal
        if g:
            lower_is_better = g.metric_key == "deaths"
            diff = g.target - g.current
            diff_color = "#22C55E" if (diff < 0 and lower_is_better) or (diff > 0 and not lower_is_better) else "#EF4444"
            sign = "+" if diff >= 0 else ""
            diff_str = f"{sign}{diff:.1f}" if g.metric_key != "damage" else f"{sign}{diff:.0f}"
            st.markdown(
                f'<div class="card cc-goal-card">'
                f'<div class="card-label">🎯 &nbsp;OBJETIVO CON {name.upper()}</div>'
                f'<div class="cc-goal-title">{g.title}</div>'
                f'<div class="cc-goal-metrics">'
                f'  <div class="cc-goal-m"><div class="cc-goal-val">{g.current:.1f}</div><div class="cc-goal-lbl">Actual</div></div>'
                f'  <div class="cc-goal-arrow">→</div>'
                f'  <div class="cc-goal-m"><div class="cc-goal-val">{g.target:.1f}</div><div class="cc-goal-lbl">Objetivo</div></div>'
                f'  <div class="cc-goal-m"><div class="cc-goal-val" style="color:{diff_color}">{diff_str}</div><div class="cc-goal-lbl">Diferencia</div></div>'
                f'</div>'
                f'<div class="cc-goal-impact">{g.impact_desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="card cc-goal-card">'
                f'<div class="card-label">🎯 &nbsp;OBJETIVO CON {name.upper()}</div>'
                f'<div class="cc-prob-desc" style="color:#6B7280">'
                f'Sin gap win/loss significativo detectado. Mantén tu nivel actual.'
                f'</div></div>',
                unsafe_allow_html=True,
            )

    # ── Fortalezas / Debilidades ──────────────────────────────────────────────
    col_s, col_w = st.columns(2, gap="medium")
    with col_s:
        items = "".join(
            f'<div class="compact-item"><span class="compact-icon-pos">✓</span>'
            f'<span class="compact-text">{s}</span></div>'
            for s in result.strengths
        ) or '<div class="compact-empty">Acumula más partidas para detectar fortalezas.</div>'
        st.markdown(
            f'<div class="card compact-card"><div class="card-label">💪 &nbsp;FORTALEZAS CON {name.upper()}</div>'
            f'{items}</div>',
            unsafe_allow_html=True,
        )
    with col_w:
        items = "".join(
            f'<div class="compact-item"><span class="compact-icon-neg">⚠</span>'
            f'<span class="compact-text">{w}</span></div>'
            for w in result.weaknesses
        ) or '<div class="compact-empty">Sin debilidades significativas detectadas.</div>'
        st.markdown(
            f'<div class="card compact-card"><div class="card-label">⚠️ &nbsp;DEBILIDADES CON {name.upper()}</div>'
            f'{items}</div>',
            unsafe_allow_html=True,
        )

    # ── Patrones adicionales ──────────────────────────────────────────────────
    remaining_patterns = result.patterns[1:]
    if remaining_patterns:
        items_html = ""
        for p in remaining_patterns:
            icon = _CC_PATTERN_ICONS.get(p.pattern_type, "📊")
            sev_c = "#EF4444" if p.severity == "critical" else "#F59E0B"
            items_html += (
                f'<div class="mi-pattern-row">'
                f'<span class="mi-pattern-icon">{icon}</span>'
                f'<span class="mi-pattern-text" style="color:{sev_c}">{p.description}</span>'
                f'</div>'
            )
        st.markdown(
            f'<div class="card mi-pattern-card">'
            f'<div class="card-label">🔍 &nbsp;PATRONES ADICIONALES</div>'
            f'{items_html}</div>',
            unsafe_allow_html=True,
        )

    # ── Integración Matchup ───────────────────────────────────────────────────
    if result.matchup_best or result.matchup_worst:
        b = result.matchup_best  or "—"
        w = result.matchup_worst or "—"
        st.markdown(
            f'<div class="card cc-matchup-row">'
            f'<div class="card-label">🗡️ &nbsp;MATCHUPS CON {name.upper()}</div>'
            f'<div style="display:flex;gap:2rem;margin-top:0.5rem">'
            f'  <div><div style="font-size:0.68rem;color:#6B7280;text-transform:uppercase;letter-spacing:0.1em">Mejor rival</div>'
            f'  <div style="font-size:1rem;font-weight:700;color:#22C55E">{b}</div></div>'
            f'  <div><div style="font-size:0.68rem;color:#6B7280;text-transform:uppercase;letter-spacing:0.1em">Peor rival</div>'
            f'  <div style="font-size:1rem;font-weight:700;color:#EF4444">{w}</div></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Post Game Review
# ---------------------------------------------------------------------------

def _render_post_game_review(role_matches: list[dict], priorities: list) -> None:
    """Sección 📝 POST GAME REVIEW — revisión rápida de la última partida."""
    st.markdown(
        '<div class="sec-header"><span class="sec-header-title">📝 &nbsp;POST GAME REVIEW</span></div>',
        unsafe_allow_html=True,
    )

    if not role_matches:
        st.markdown(
            '<div class="card" style="color:#6B7280;font-size:0.85rem;padding:1.2rem 1.5rem">'
            'Sin partidas registradas en este rol.</div>',
            unsafe_allow_html=True,
        )
        return

    # Selector de partida (las últimas 5)
    opts = {}
    for m in role_matches[:5]:
        champ  = m.get("champion", "?")
        result = "✓" if m.get("result") == "WIN" else "✗"
        date   = (m.get("played_at") or "")[:10]
        label  = f"{result} {champ} — {date}"
        opts[label] = m

    if not opts:
        return

    selected_label = st.selectbox(
        "Partida",
        list(opts.keys()),
        key="pgr_match_select",
        label_visibility="collapsed",
    )
    match = opts[selected_label]
    champion = match.get("champion", "?")

    # Patrones del Champion Coach para este campeón
    from backend.services.champion_coach import analyze_champion as _analyze_champ
    cc = _analyze_champ(role_matches, champion, role_matches[0].get("role", "ADC"))
    patterns = cc.patterns if cc else []

    review: PostGameReview = generate_review(
        match           = match,
        player_history  = role_matches,
        champion_patterns = patterns,
        priorities      = priorities,
    )

    # ── Cabecera: resultado + score ───────────────────────────────────────────
    result_text  = "VICTORIA" if review.result == "WIN" else "DERROTA"
    result_color = "#22C55E"  if review.result == "WIN" else "#EF4444"
    score_str    = f"{review.score:.0f}" if review.score is not None else "—"
    avg_str      = f"{review.score_avg:.0f}" if review.score_avg is not None else "—"
    delta_str    = ""
    if review.score_delta is not None:
        sign = "+" if review.score_delta >= 0 else ""
        delta_color = "#22C55E" if review.score_delta >= 0 else "#EF4444"
        delta_str = f'<span style="color:{delta_color};font-size:0.85rem;margin-left:0.5rem">{sign}{review.score_delta:.0f} vs promedio</span>'

    conf_map = {"low": "⚠️ Muestra baja", "medium": "📊 Preliminar", "high": "✅ Confiable"}
    conf_str = conf_map.get(review.confidence, "—")

    st.markdown(
        f'<div class="card pgr-hero">'
        f'  <div class="pgr-hero-left">'
        f'    <div class="pgr-result" style="color:{result_color}">{result_text}</div>'
        f'    <div class="pgr-champ">{review.champion}</div>'
        f'    <div class="pgr-rating" style="color:{review.rating_color}">{review.rating}</div>'
        f'  </div>'
        f'  <div class="pgr-hero-right">'
        f'    <div class="pgr-score-block">'
        f'      <div class="pgr-score-val">{score_str}{delta_str}</div>'
        f'      <div class="pgr-score-lbl">Score · Promedio reciente: {avg_str}</div>'
        f'    </div>'
        f'    <div class="pgr-conf">{conf_str}</div>'
        f'  </div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Lo mejor / Lo peor ───────────────────────────────────────────────────
    col_ok, col_bad = st.columns(2, gap="medium")

    with col_ok:
        items = "".join(
            f'<div class="compact-item"><span class="compact-icon-pos">✓</span>'
            f'<span class="compact-text">{s}</span></div>'
            for s in review.strengths
        ) or '<div class="compact-empty">Sin mejoras destacables respecto a tu promedio.</div>'
        st.markdown(
            f'<div class="card compact-card"><div class="card-label">✅ &nbsp;LO MEJOR</div>'
            f'{items}</div>',
            unsafe_allow_html=True,
        )

    with col_bad:
        items = "".join(
            f'<div class="compact-item"><span class="compact-icon-neg">⚠</span>'
            f'<span class="compact-text">{e}</span></div>'
            for e in review.mistakes
        ) or '<div class="compact-empty">Sin errores destacables respecto a tu promedio.</div>'
        st.markdown(
            f'<div class="card compact-card"><div class="card-label">⚠️ &nbsp;LO PEOR</div>'
            f'{items}</div>',
            unsafe_allow_html=True,
        )

    # ── Foco próxima partida ──────────────────────────────────────────────────
    if review.focus:
        st.markdown(
            f'<div class="card pgr-focus">'
            f'  <div class="card-label">🎯 &nbsp;PRÓXIMA PARTIDA</div>'
            f'  <div class="pgr-focus-text">{review.focus}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Comparaciones métricas ────────────────────────────────────────────────
    if review.comparisons:
        verdict_color = {"Mejor de lo normal": "#22C55E", "Peor de lo normal": "#EF4444", "Normal": "#6B7280"}
        rows_html = ""
        for c in review.comparisons:
            vc = verdict_color.get(c.verdict, "#6B7280")
            rows_html += (
                f'<div class="pgr-cmp-row">'
                f'  <div class="pgr-cmp-label">{c.label}</div>'
                f'  <div class="pgr-cmp-now">{c.current:.1f} <span class="pgr-cmp-unit">{c.unit}</span></div>'
                f'  <div class="pgr-cmp-avg">Promedio: {c.avg:.1f}</div>'
                f'  <div class="pgr-cmp-verdict" style="color:{vc}">{c.verdict}</div>'
                f'</div>'
            )
        st.markdown(
            f'<div class="card pgr-cmp-card">'
            f'<div class="card-label">📊 &nbsp;COMPARACIÓN vs PROMEDIO</div>'
            f'{rows_html}'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Contexto matchup ──────────────────────────────────────────────────────
    if review.matchup_context:
        st.markdown(
            f'<div class="card pgr-matchup">'
            f'<div class="card-label">🗡️ &nbsp;MATCHUP</div>'
            f'<div class="pgr-matchup-text">{review.matchup_context}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Problema recurrente del Champion Coach ────────────────────────────────
    if review.champion_problem:
        repeat_html = ""
        if review.pattern_repeated:
            repeat_html = '<div class="pgr-repeat-badge">Patrón repetido detectado hoy</div>'
        st.markdown(
            f'<div class="card pgr-champ-prob">'
            f'<div class="card-label">🏅 &nbsp;PROBLEMA RECURRENTE CON {review.champion.upper()}</div>'
            f'<div class="pgr-champ-prob-text">{review.champion_problem}</div>'
            f'{repeat_html}'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Errores repetidos ─────────────────────────────────────────────────────
    if review.repeated_mistakes:
        items_html = "".join(
            f'<div class="pgr-rep-item">🔁 {e}</div>'
            for e in review.repeated_mistakes
        )
        st.markdown(
            f'<div class="card pgr-rep-card">'
            f'<div class="card-label">🔁 &nbsp;ERRORES REPETIDOS</div>'
            f'{items_html}'
            f'</div>',
            unsafe_allow_html=True,
        )


_CI_MIN_GAMES = 10   # partidas mínimas para análisis Champion Intelligence

# ---------------------------------------------------------------------------
# Matchup Intelligence
# ---------------------------------------------------------------------------

_MI_MIN_COVERAGE = 5   # mínimo de partidas con raw JSON para mostrar la sección


def _conf_badge(confidence: str) -> str:
    if confidence == "high":
        return '<span class="mi-badge high">confiable</span>'
    if confidence == "medium":
        return '<span class="mi-badge medium">preliminar</span>'
    return '<span class="mi-badge low">muestra baja</span>'


def _wr_bar(wr: float) -> str:
    pct   = round(wr * 100)
    color = _wr_color(wr)
    return (
        f'<div class="mi-wr-bar-track">'
        f'<div class="mi-wr-bar-fill" style="width:{pct}%;background:{color}"></div>'
        f'</div>'
    )


def _matchup_row_html(r: MatchupRecord, label_color: str) -> str:
    wr_c   = _wr_color(r.winrate)
    badge  = _conf_badge(r.confidence)
    bar    = _wr_bar(r.winrate)
    deaths = f"{r.avg_deaths:.1f}"
    cs     = f"{r.avg_cs_min:.1f}" if r.avg_cs_min else "—"
    return (
        f'<div class="mi-row">'
        f'  <div class="mi-row-name" style="color:{label_color}">{r.enemy}</div>'
        f'  <div class="mi-row-meta">{r.games}P {badge}</div>'
        f'  <div class="mi-row-wr" style="color:{wr_c}">{r.winrate:.0%}</div>'
        f'  {bar}'
        f'  <div class="mi-row-stats">'
        f'    <span class="mi-row-stat">💀 {deaths}</span>'
        f'    <span class="mi-row-stat">🌾 {cs}/min</span>'
        f'  </div>'
        f'</div>'
    )


def _render_matchup_intelligence(result: MatchupResult) -> None:
    st.markdown(
        '<div class="sec-header"><span class="sec-header-title">🗡️ &nbsp;MATCHUP INTELLIGENCE</span></div>',
        unsafe_allow_html=True,
    )

    if result.raw_coverage < _MI_MIN_COVERAGE:
        st.markdown(
            f'<div class="card mi-insuf">'
            f'  <div class="mi-insuf-title">Datos insuficientes</div>'
            f'  <div class="mi-insuf-sub">'
            f'    Se necesitan al menos {_MI_MIN_COVERAGE} partidas con datos de rivales disponibles. '
            f'    Actualmente: {result.raw_coverage} / {_MI_MIN_COVERAGE}.'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Fila superior: Mejores / Peores / Ban ───────────────────────────────
    col_best, col_worst, col_ban = st.columns([1, 1, 1], gap="medium")

    with col_best:
        rows_html = "".join(_matchup_row_html(r, "#22C55E") for r in result.best)
        no_data   = '<div class="mi-empty">Sin matchups favorables con muestra suficiente aún.</div>'
        st.markdown(
            f'<div class="card mi-card">'
            f'<div class="card-label">✅ &nbsp;MEJORES MATCHUPS</div>'
            f'{rows_html or no_data}'
            f'</div>',
            unsafe_allow_html=True,
        )

    with col_worst:
        rows_html = "".join(_matchup_row_html(r, "#EF4444") for r in result.worst)
        no_data   = '<div class="mi-empty">Sin matchups problemáticos identificados aún.</div>'
        st.markdown(
            f'<div class="card mi-card">'
            f'<div class="card-label">❌ &nbsp;PEORES MATCHUPS</div>'
            f'{rows_html or no_data}'
            f'</div>',
            unsafe_allow_html=True,
        )

    with col_ban:
        ban = result.ban
        if ban:
            wr_c     = _wr_color(ban.winrate)
            badge    = _conf_badge(ban.confidence)
            bar      = _wr_bar(ban.winrate)
            reasons_html = "".join(
                f'<div class="mi-ban-reason">• {r}</div>'
                for r in ban.reasons
            )
            st.markdown(
                f'<div class="card mi-card mi-ban-card">'
                f'<div class="card-label">🚫 &nbsp;BAN RECOMENDADO</div>'
                f'<div class="mi-ban-name">{ban.enemy}</div>'
                f'<div class="mi-ban-meta">{ban.games}P &nbsp;·&nbsp; '
                f'<span style="color:{wr_c};font-weight:700">{ban.winrate:.0%} WR</span>'
                f' {badge}</div>'
                f'{bar}'
                f'<div class="mi-ban-reasons">{reasons_html}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div class="card mi-card"><div class="card-label">🚫 &nbsp;BAN RECOMENDADO</div>'
                '<div class="mi-empty">Sin datos suficientes para recomendar un ban.</div>'
                '</div>',
                unsafe_allow_html=True,
            )

    # ── Patrones detectados ─────────────────────────────────────────────────
    if result.patterns:
        critical = [p for p in result.patterns if p.severity == "critical"]
        warnings = [p for p in result.patterns if p.severity == "warning"]

        items_html = ""
        for p in critical + warnings:
            icon = "🔴" if p.severity == "critical" else "🟡"
            items_html += (
                f'<div class="mi-pattern-row">'
                f'<span class="mi-pattern-icon">{icon}</span>'
                f'<span class="mi-pattern-text">{p.description}</span>'
                f'</div>'
            )

        st.markdown(
            f'<div class="card mi-pattern-card">'
            f'<div class="card-label">🔍 &nbsp;PATRONES DETECTADOS</div>'
            f'{items_html}'
            f'</div>',
            unsafe_allow_html=True,
        )


def _render_champion_intelligence(cpa, n_role_matches: int = 0) -> None:

    st.markdown(
        '<div class="sec-header"><span class="sec-header-title">🏆 &nbsp;CHAMPION INTELLIGENCE</span></div>',
        unsafe_allow_html=True,
    )

    if n_role_matches < _CI_MIN_GAMES:
        progress_pct = round(n_role_matches / _CI_MIN_GAMES * 100)
        st.markdown(
            f'<div class="card ci-insuf">'
            f'  <div class="ci-insuf-title">Datos insuficientes</div>'
            f'  <div class="ci-insuf-sub">'
            f'    Necesitas al menos {_CI_MIN_GAMES} partidas en este rol para activar Champion Intelligence.'
            f'  </div>'
            f'  <div class="ci-insuf-progress">'
            f'    <div class="ci-insuf-bar-track">'
            f'      <div class="ci-insuf-bar-fill" style="width:{progress_pct}%"></div>'
            f'    </div>'
            f'    <div class="ci-insuf-count">{n_role_matches} / {_CI_MIN_GAMES} partidas</div>'
            f'  </div>'
            f'  <div class="ci-insuf-tip">Consejo: juega al menos 3 partidas por campeón para un análisis de pool completo.</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        return

    if cpa.total_games == 0:
        st.markdown(
            '<div class="card" style="color:#6B7280;font-size:0.85rem;padding:1.2rem 1.5rem">'
            'Datos insuficientes para analizar tu champion pool.</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Barra de grade ──────────────────────────────────────────────────
    grade_color = _grade_color(cpa.grade)
    grade_descs = {
        "A": "Pool sólido y diverso. Puedes adaptarte al draft.",
        "B": "Buen pool con margen de mejora.",
        "C": "Pool funcional pero con vulnerabilidades.",
        "D": "Pool estrecho o con picks problemáticos.",
        "F": "Datos insuficientes o pool en crisis.",
    }
    grade_desc = grade_descs.get(cpa.grade, "")
    st.markdown(
        f'<div class="ci-grade-bar">'
        f'  <div class="ci-grade-letter" style="color:{grade_color}">{cpa.grade}</div>'
        f'  <div>'
        f'    <div class="ci-grade-label" style="color:{grade_color}">Champion Pool Score</div>'
        f'    <div class="ci-grade-score">{cpa.grade_score:.0f}/100 · {cpa.total_games} partidas · {cpa.pool_depth} campeones calificados</div>'
        f'  </div>'
        f'  <div class="ci-grade-desc" style="margin-left:auto;max-width:260px">{grade_desc}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Tarjetas de clasificación ────────────────────────────────────────
    clf = cpa.classification
    trap_names = {t.champion for t in clf.trap}

    def _class_card(css_type: str, tag: str, stats) -> str:
        if stats is None:
            return (
                f'<div class="ci-class-card {css_type}">'
                f'  <div class="ci-class-tag {css_type}">{tag}</div>'
                f'  <div class="ci-class-name" style="color:#6B7280">—</div>'
                f'  <div class="ci-class-meta">Sin datos suficientes</div>'
                f'</div>'
            )
        wr_c = _wr_color(stats.winrate)
        return (
            f'<div class="ci-class-card {css_type}">'
            f'  <div class="ci-class-tag {css_type}">{tag}</div>'
            f'  <div class="ci-class-name">{stats.champion}</div>'
            f'  <div class="ci-class-meta">'
            f'    {stats.games}P &nbsp;·&nbsp; '
            f'    <span style="color:{wr_c};font-weight:700">{stats.winrate:.0%} WR</span>'
            f'    &nbsp;·&nbsp; Score {stats.avg_score:.0f}'
            f'  </div>'
            f'</div>'
        )

    main_tag = "MAIN + TRAP" if (clf.main and clf.main.champion in trap_names) else "MAIN"
    main_css = "trap" if (clf.main and clf.main.champion in trap_names) else "main"

    st.markdown(
        f'<div class="ci-class-grid">'
        + _class_card(main_css,    main_tag,    clf.main)
        + _class_card("carry",     "CARRY",     clf.carry)
        + _class_card("comfort",   "COMFORT",   clf.comfort)
        + (
            _class_card("trap", "TRAP", clf.trap[0])
            if clf.trap and (clf.main is None or clf.trap[0].champion != clf.main.champion)
            else _class_card("trap", "TRAP", None)
        )
        + f'</div>',
        unsafe_allow_html=True,
    )

    # ── Tabla de campeones ───────────────────────────────────────────────
    if cpa.champions:
        header_html = (
            '<div class="ci-champ-row" style="border-bottom:1px solid rgba(255,255,255,0.08);padding-bottom:0.4rem;margin-bottom:0.2rem">'
            '<div class="ci-champ-name" style="color:#6B7280;font-size:0.68rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase">CAMPEÓN</div>'
            '<div class="ci-champ-games" style="color:#6B7280;font-size:0.68rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase">PARTIDAS</div>'
            '<div class="ci-champ-wr" style="color:#6B7280;font-size:0.68rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase">WR</div>'
            '<div class="ci-champ-score" style="color:#6B7280;font-size:0.68rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase">SCORE</div>'
            '<div class="ci-champ-trend" style="color:#6B7280;font-size:0.68rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase">TEND.</div>'
            '</div>'
        )
        rows_html = ""
        for cs in cpa.champions:
            wr_c = _wr_color(cs.winrate)
            is_trap = cs.champion in trap_names
            name_color = "#EF4444" if is_trap else "#D1D5DB"
            rows_html += (
                f'<div class="ci-champ-row">'
                f'<div class="ci-champ-name" style="color:{name_color}">'
                f'{cs.champion}{"  ⚠" if is_trap else ""}</div>'
                f'<div class="ci-champ-games">{cs.games}</div>'
                f'<div class="ci-champ-wr" style="color:{wr_c}">{cs.winrate:.0%}</div>'
                f'<div class="ci-champ-score">{cs.avg_score:.0f}</div>'
                f'<div class="ci-champ-trend">{_trend_icon(cs.score_trend)}</div>'
                f'</div>'
            )

        st.markdown(
            '<div class="card" style="margin-bottom:0.85rem">'
            '<div class="card-label">TOP CAMPEONES</div>'
            + header_html + rows_html +
            '</div>',
            unsafe_allow_html=True,
        )

    # ── Insights ─────────────────────────────────────────────────────────
    if cpa.insights:
        icons = {"warning": "⚠️", "info": "ℹ️", "positive": "✅"}
        insights_html = ""
        for ins in cpa.insights:
            insights_html += (
                f'<div class="ci-insight {ins.level}">'
                f'<div class="ci-insight-icon">{icons[ins.level]}</div>'
                f'<div class="ci-insight-text">{ins.text}</div>'
                f'</div>'
            )
        st.markdown(
            '<div class="card-label" style="margin-bottom:0.5rem">RIESGOS Y OPORTUNIDADES</div>'
            + insights_html,
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Render principal
# ---------------------------------------------------------------------------

def render() -> None:
    if not db.get_config("puuid"):
        st.markdown(
            '<div class="locked-screen">'
            '<div class="ls-icon">🔒</div>'
            '<div class="ls-title">Coaching no disponible</div>'
            '<div class="ls-body">Configura tu cuenta en <b>Configuración</b> para activar el coaching personalizado.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    # ── Selectores (determinan qué construye el ViewModel) ────────────────────
    col_h, col_rol, col_win, col_sync = st.columns([3, 1, 1.5, 1.2], gap="small")
    window_opts = {"Últimas 10": 10, "Últimas 20": 20, "Últimas 30": 30, "Todas": 200}
    with col_rol:
        role = st.selectbox("Rol", ["ADC", "TOP"], key="coaching_role", label_visibility="collapsed")
    with col_win:
        window_lbl = st.selectbox("Ventana", list(window_opts.keys()), index=1, key="coaching_window", label_visibility="collapsed")

    # ── Construir ViewModel (toda la lógica de datos vive aquí) ──────────────
    limit = window_opts[window_lbl]
    vm    = build_coaching(role, limit)

    # ── Header (requiere vm para nombre y fecha) ──────────────────────────────
    with col_h:
        st.markdown(
            f'<div class="pg-title">¡Hola, {vm.player_name}! 👋</div>'
            '<div class="pg-subtitle">Aquí tienes tu plan de mejora personalizado.</div>',
            unsafe_allow_html=True,
        )
    with col_sync:
        if vm.last_match_date:
            st.markdown(f'<div class="pg-sync">Datos al {vm.last_match_date}</div>', unsafe_allow_html=True)
    st.markdown('<hr style="margin:0.75rem 0 1.25rem">', unsafe_allow_html=True)

    if not vm.has_data:
        st.info(f"No hay partidas de {role} guardadas. Ve a **Partidas** y descarga tu historial.")
        return

    sr         = vm.score_result
    cr         = vm.coaching_result
    mx         = dataclasses.asdict(vm.metrics)
    priorities = vm.priorities
    matchups   = vm.matchup_result
    role_matches = vm.role_matches

    # ── Nivel 0: Alerta de sesión ─────────────────────────
    _render_session_alert(cr.session_warning)

    # ── Nivel 1: Hero — Score + contexto inmediato ────────
    _render_hero(sr, mx, cr)

    # ── Nivel 1.5: Mayores ganancias potenciales ──────────
    _render_priorities(priorities)

    # ── Nivel 2+3: Problema Principal + Objetivo Semanal ──
    c_prob, c_obj = st.columns([2, 1], gap="medium")
    with c_prob:
        _render_problema(cr, mx)
    with c_obj:
        _render_objetivo(cr)

    # ── Nivel 4: Plan de Entrenamiento ────────────────────
    st.markdown('<div style="margin-top:0.25rem"></div>', unsafe_allow_html=True)
    _render_plan(cr)

    # ── Nivel 5: Fortalezas y Debilidades (compacto) ──────
    st.markdown('<div class="sec-header"><span class="sec-header-title">💪 &nbsp;RENDIMIENTO</span></div>', unsafe_allow_html=True)
    _render_strengths_weaknesses(cr, role)

    # ── Champion Intelligence ──────────────────────────────
    _render_champion_intelligence(vm.champion_pool, n_role_matches=vm.sample_size)

    # ── Matchup Intelligence ───────────────────────────────
    _render_matchup_intelligence(matchups)

    # ── Post Game Review ──────────────────────────────────
    _render_post_game_review(role_matches, priorities)

    # ── Champion Coach ─────────────────────────────────────
    st.markdown(
        '<div class="sec-header"><span class="sec-header-title">🏅 &nbsp;CHAMPION COACH</span></div>',
        unsafe_allow_html=True,
    )
    if vm.available_champions:
        selected_champ = st.selectbox(
            "Selecciona campeón",
            vm.available_champions,
            key="cc_champion_select",
            label_visibility="collapsed",
        )
        cc_result = build_champion_coach(vm, selected_champ)
        _render_champion_coach(cc_result, role)
    else:
        st.info(f"No hay partidas de {role} guardadas para Champion Coach.")

    # ── Evolución (gráficos) ───────────────────────────────
    st.markdown('<div class="sec-header"><span class="sec-header-title">📈 &nbsp;EVOLUCIÓN</span></div>', unsafe_allow_html=True)
    _render_trend_chart(sr, mx, role_matches)

    # ── Datos Avanzados ────────────────────────────────────
    st.markdown('<div class="sec-header"><span class="sec-header-title">📊 &nbsp;DATOS AVANZADOS</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="card" style="margin-bottom:1rem">', unsafe_allow_html=True)
    _render_datos_avanzados(mx, sr.benchmarks, role)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Resumen de partidas ────────────────────────────────
    _render_match_summary(role_matches, sr.match_scores)

    # ── Info bar ──────────────────────────────────────────
    conf_labels = {
        "insufficient": "⚠️ Datos insuficientes",
        "preliminary":  "📊 Datos preliminares",
        "reliable":     "✅ Análisis confiable",
        "robust":       "✅ Análisis robusto",
    }
    conf_str = conf_labels.get(cr.confidence_level, cr.confidence_level)
    st.markdown(
        f'<div class="info-bar">'
        f'<span style="color:#3B82F6">ℹ️</span>'
        f'<span style="color:#9CA3AF"><b style="color:#D1D5DB">Acción clave:</b> '
        f'{cr.training_plan.primary}</span>'
        f'<span style="margin-left:auto;color:#6B7280">{conf_str} · N={cr.sample_size} partidas {role}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
