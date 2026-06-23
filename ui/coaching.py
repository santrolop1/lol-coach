"""
ui/coaching.py — Página principal de coaching personalizado.

Conecta scorer_v2 + coaching_engine con la interfaz premium.
Roles soportados: ADC, TOP.
"""

import sys
import statistics
from pathlib import Path
from datetime import datetime, timezone

import streamlit as st
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).parent.parent))

import db
import scorer_v2
import coaching_engine
import coaching_rules
from backend.services.champion_analyzer import analyze_champion_pool


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
        height=160, margin=dict(l=0, r=10, t=5, b=25),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            showgrid=False, zeroline=False,
            tickvals=tvals, ticktext=ttext,
            tickfont=dict(color="#374151", size=10), showline=False,
        ),
        yaxis=dict(
            showgrid=True, gridcolor="rgba(255,255,255,0.03)",
            zeroline=False, tickfont=dict(color="#374151", size=10),
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
        height=190, margin=dict(l=0, r=10, t=5, b=25),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(
            showgrid=False, zeroline=False,
            tickvals=tvals, ticktext=ttext,
            tickfont=dict(color="#374151", size=10), showline=False,
        ),
        yaxis=dict(
            showgrid=True, gridcolor="rgba(255,255,255,0.03)",
            zeroline=False, tickfont=dict(color="#374151", size=10), range=[0, 105],
        ),
        showlegend=False, hovermode="x unified",
    )
    return fig


# ---------------------------------------------------------------------------
# Cómputo de métricas desde partidas crudas
# ---------------------------------------------------------------------------

def _compute_metrics(matches: list[dict]) -> dict:
    """Extrae promedios de métricas relevantes desde datos crudos."""
    if not matches:
        return {}
    dur_mins = [max(m.get("duration_sec", 60) / 60, 1.0) for m in matches]
    wins   = [m for m in matches if m.get("result") == "WIN"]
    losses = [m for m in matches if m.get("result") == "LOSS"]

    def avg_field(lst, key):
        vals = [_safe(m, key) for m in lst]
        vals = [v for v in vals if v is not None]
        return _avg(vals) if vals else None

    def avg_pm(lst, key):
        vals = [_safe(m, key) for m in lst]
        durs = [max(m.get("duration_sec", 60) / 60, 1.0) for m in lst]
        pairs = [(v, d) for v, d in zip(vals, durs) if v is not None]
        return _avg([v / d for v, d in pairs]) if pairs else None

    deaths_all  = avg_field(matches, "deaths")
    deaths_win  = avg_field(wins,    "deaths")
    deaths_loss = avg_field(losses,  "deaths")

    kp_vals = [_safe(m, "kill_participation") for m in matches]
    kp_vals = [v for v in kp_vals if v is not None]
    kp_win  = [_safe(m, "kill_participation") for m in wins if _safe(m, "kill_participation") is not None]
    kp_loss = [_safe(m, "kill_participation") for m in losses if _safe(m, "kill_participation") is not None]

    vs_vals = [_safe(m, "vision_score") for m in matches]
    vs_vals = [v for v in vs_vals if v is not None]

    return {
        "cs_pm":       avg_pm(matches, "cs"),
        "dmg_pm":      avg_pm(matches, "damage"),
        "kp":          _avg(kp_vals) if kp_vals else None,
        "kp_win":      _avg(kp_win)  if kp_win  else None,
        "kp_loss":     _avg(kp_loss) if kp_loss else None,
        "deaths":      deaths_all,
        "deaths_win":  deaths_win,
        "deaths_loss": deaths_loss,
        "vision_pm":   avg_pm(matches, "vision_score"),
        "gold_pm":     avg_pm(matches, "gold_earned"),
        "obj_pm":      avg_pm(matches, "objective_damage"),
        "n":           len(matches),
        "n_wins":      len(wins),
        "n_losses":    len(losses),
    }


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


def _render_level_and_trend(sr, mx: dict) -> None:
    score = sr.overall_score or 50.0
    label, color = _tier(score)

    # Calcular delta entre primera y segunda mitad
    all_sc = [ms.overall_score for ms in sr.match_scores if ms.overall_score is not None]
    trend_delta_str = "—"
    trend_color = "#374151"
    if len(all_sc) >= 6:
        mid = len(all_sc) // 2
        recent_avg = _avg(all_sc[:mid])   # más reciente (newest first)
        older_avg  = _avg(all_sc[mid:])
        delta = recent_avg - older_avg
        sign = "+" if delta >= 0 else ""
        trend_delta_str = f"{sign}{delta:.0f}"
        trend_color = "#22C55E" if delta >= 0 else "#EF4444"

    col_level, col_trend = st.columns([1, 2], gap="medium")

    with col_level:
        st.markdown(
            '<div class="card">'
            f'<div class="card-label">TU NIVEL ACTUAL</div>',
            unsafe_allow_html=True,
        )
        fig = _ring_chart(score, color)
        st.plotly_chart(fig, use_container_width=False, config={"displayModeBar": False})
        n_wins = mx.get("n_wins", 0)
        n_tot  = mx.get("n", 1)
        wr     = n_wins / n_tot * 100 if n_tot else 0
        st.markdown(
            f'<div class="level-tier" style="color:{color}">{label}</div>'
            f'<div class="level-sub">Score auto-relativo (tu historial)</div>'
            f'<div class="level-pct">WR {wr:.0f}% · {n_wins}/{n_tot} partidas</div>'
            '</div>',
            unsafe_allow_html=True,
        )

    with col_trend:
        st.markdown(
            '<div class="card">'
            '<div class="card-label">TENDENCIA GENERAL</div>',
            unsafe_allow_html=True,
        )
        fig2 = _sparkline(sr.match_scores)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
        trend_map = {"improving": "Mejorando ↑", "stable": "Estable →", "declining": "Bajando ↓"}
        trend_lbl = trend_map.get(sr.trend, "Estable →")
        st.markdown(
            f'<div class="trend-delta" style="color:{trend_color}">{trend_delta_str}</div>'
            f'<div class="trend-vs">vs ventana anterior · {trend_lbl}</div>'
            '</div>',
            unsafe_allow_html=True,
        )


def _render_objetivo(cr) -> None:
    goal = cr.weekly_goal
    if not goal:
        return
    metric = goal.metric
    cur_str = _format_goal_value(goal.current, metric)
    tgt_str = _format_goal_value(goal.target,  metric)
    pct     = _goal_progress_pct(goal.current, goal.target, metric)

    st.markdown(
        f'<div class="goal-card">'
        f'<div class="card-label" style="display:flex;align-items:center;gap:6px">'
        f'🎯 &nbsp;TU OBJETIVO SEMANAL</div>'
        f'<div class="goal-title">{cr.primary_problem.upper()}</div>'
        f'<div style="font-size:0.68rem;color:#374151;margin-bottom:0.5rem">Actual</div>'
        f'<div class="goal-row">'
        f'<div class="goal-current">{cur_str}</div>'
        f'<div class="goal-arrow">»</div>'
        f'<div style="flex:1">'
        f'<div style="font-size:0.68rem;color:#374151;margin-bottom:2px">Objetivo</div>'
        f'<div class="goal-target">{tgt_str}</div>'
        f'</div></div>'
        f'<div class="goal-bar-track">'
        f'<div class="goal-bar-fill" style="width:{pct:.0f}%"></div>'
        f'</div>'
        f'<div class="goal-meta">'
        f'<span>Progreso <span class="goal-meta-val">{pct:.0f}%</span></span>'
        f'<span>Ventana: <b style="color:#6B7280">{goal.window}</b></span>'
        f'</div>'
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

    str_icons = ["🛡️", "👥", "🌾", "⚡", "📈"]
    wk_icons  = ["💀", "🎯", "📊", "🏯", "👁️"]

    with col_s:
        st.markdown(
            '<div class="card" style="min-height:180px">'
            '<div class="card-label">💪 &nbsp;TUS FORTALEZAS</div>',
            unsafe_allow_html=True,
        )
        if cr.strengths:
            for i, s in enumerate(cr.strengths):
                st.markdown(
                    f'<div class="str-item">'
                    f'<div class="str-icon">{str_icons[i % len(str_icons)]}</div>'
                    f'<div>'
                    f'<div class="str-name">{s.name.upper()}</div>'
                    f'<div class="str-evidence">{s.evidence}</div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(
                '<p style="font-size:0.8rem;color:#374151;margin-top:0.5rem">'
                'Sigue jugando para detectar fortalezas consistentes.</p>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

    with col_w:
        st.markdown(
            '<div class="card" style="min-height:180px">'
            '<div class="card-label">🔥 &nbsp;TUS DEBILIDADES</div>',
            unsafe_allow_html=True,
        )
        # Primary problem
        main_icon = _problem_icon(cr.primary_problem)
        st.markdown(
            f'<div class="wk-item">'
            f'<div class="wk-icon">{main_icon}</div>'
            f'<div>'
            f'<div class="wk-name">{cr.primary_problem.upper()}</div>'
            f'<div class="wk-evidence">{cr.impact}</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )
        for i, imp in enumerate(cr.improvements):
            st.markdown(
                f'<div class="wk-item">'
                f'<div class="wk-icon">{wk_icons[(i + 1) % len(wk_icons)]}</div>'
                f'<div>'
                f'<div class="wk-name">{imp.upper()}</div>'
                f'<div class="wk-evidence">{_impact_for(imp, role) or "Área de mejora identificada en tu historial."}</div>'
                f'</div></div>',
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
            f'<div style="font-size:0.64rem;color:#374151;font-weight:700;letter-spacing:0.12em;text-transform:uppercase">Última</div>'
            f'<div style="font-size:1.8rem;font-weight:900;color:#8B5CF6;line-height:1">{last_str}</div>'
            f'</div>'
            f'<div>'
            f'<div style="font-size:0.64rem;color:#374151;font-weight:700;letter-spacing:0.12em;text-transform:uppercase">Mejor</div>'
            f'<div style="font-size:1.8rem;font-weight:900;color:#22C55E;line-height:1">{best_str}</div>'
            f'</div>'
            f'<div>'
            f'<div style="font-size:0.64rem;color:#374151;font-weight:700;letter-spacing:0.12em;text-transform:uppercase">Peor</div>'
            f'<div style="font-size:1.8rem;font-weight:900;color:#EF4444;line-height:1">{worst_str}</div>'
            f'</div>'
            f'<div style="border-top:1px solid rgba(255,255,255,0.05);padding-top:1rem;margin-top:0.5rem">'
            f'<div class="card-label" style="margin-bottom:0.25rem">MUERTES</div>'
            f'</div>'
            f'<div>'
            f'<div style="font-size:0.64rem;color:#374151;font-weight:700;letter-spacing:0.12em;text-transform:uppercase">Promedio</div>'
            f'<div style="font-size:1.8rem;font-weight:900;color:#F59E0B;line-height:1">{avg_deaths_str}</div>'
            f'</div>'
            f'<div>'
            f'<div style="font-size:0.64rem;color:#374151;font-weight:700;letter-spacing:0.12em;text-transform:uppercase">Mejor</div>'
            f'<div style="font-size:1.8rem;font-weight:900;color:#22C55E;line-height:1">{best_deaths}</div>'
            f'</div>'
            f'<div>'
            f'<div style="font-size:0.64rem;color:#374151;font-weight:700;letter-spacing:0.12em;text-transform:uppercase">Peor</div>'
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
    return {"A": "#22C55E", "B": "#8B5CF6", "C": "#3B82F6", "D": "#F59E0B", "F": "#EF4444"}.get(grade, "#374151")


def _wr_color(wr: float) -> str:
    if wr >= 0.55: return "#22C55E"
    if wr >= 0.45: return "#F59E0B"
    return "#EF4444"


def _trend_icon(slope: float) -> str:
    if slope > 1.5:  return '<span style="color:#22C55E">↑</span>'
    if slope < -1.5: return '<span style="color:#EF4444">↓</span>'
    return '<span style="color:#374151">→</span>'


def _render_champion_intelligence(cpa) -> None:

    st.markdown(
        '<div class="sec-header"><span class="sec-header-title">🏆 &nbsp;CHAMPION INTELLIGENCE</span></div>',
        unsafe_allow_html=True,
    )

    if cpa.total_games == 0:
        st.markdown(
            '<div class="card" style="color:#374151;font-size:0.85rem;padding:1.2rem 1.5rem">'
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
                f'  <div class="ci-class-name" style="color:#374151">—</div>'
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
            '<div class="ci-champ-name" style="color:#374151;font-size:0.68rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase">CAMPEÓN</div>'
            '<div class="ci-champ-games" style="color:#374151;font-size:0.68rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase">PARTIDAS</div>'
            '<div class="ci-champ-wr" style="color:#374151;font-size:0.68rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase">WR</div>'
            '<div class="ci-champ-score" style="color:#374151;font-size:0.68rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase">SCORE</div>'
            '<div class="ci-champ-trend" style="color:#374151;font-size:0.68rem;font-weight:700;letter-spacing:0.1em;text-transform:uppercase">TEND.</div>'
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
    puuid = db.get_config("puuid")
    if not puuid:
        st.markdown(
            '<div class="locked-screen">'
            '<div class="ls-icon">🔒</div>'
            '<div class="ls-title">Coaching no disponible</div>'
            '<div class="ls-body">Configura tu cuenta en <b>Configuración</b> para activar el coaching personalizado.</div>'
            '</div>',
            unsafe_allow_html=True,
        )
        return

    player = db.get_player(puuid)
    name   = player["riot_id"] if player else "Invocador"
    rank   = player.get("rank", "Sin rango") if player else "—"
    lp     = player.get("lp", 0) if player else 0

    # ── Header ───────────────────────────────────────────
    col_h, col_rol, col_win, col_sync = st.columns([3, 1, 1.5, 1.2], gap="small")
    with col_h:
        st.markdown(
            f'<div class="pg-title">¡Hola, {name}! 👋</div>'
            '<div class="pg-subtitle">Aquí tienes tu plan de mejora personalizado.</div>',
            unsafe_allow_html=True,
        )
    with col_rol:
        role = st.selectbox("Rol", ["ADC", "TOP"], key="coaching_role", label_visibility="collapsed")
    with col_win:
        window_opts = {"Últimas 10": 10, "Últimas 20": 20, "Últimas 30": 30, "Todas": 200}
        window_lbl  = st.selectbox("Ventana", list(window_opts.keys()), index=1, key="coaching_window", label_visibility="collapsed")
    with col_sync:
        all_m = db.get_matches(puuid, limit=1)
        if all_m and all_m[0].get("played_at"):
            last_date = all_m[0]["played_at"][:10]
            st.markdown(f'<div class="pg-sync">Datos al {last_date}</div>', unsafe_allow_html=True)

    st.markdown('<hr style="margin:0.75rem 0 1.25rem">', unsafe_allow_html=True)

    # ── Obtener datos ─────────────────────────────────────
    limit       = window_opts[window_lbl]
    all_matches = db.get_matches(puuid, limit=max(limit + 50, 200))
    role_matches = [m for m in all_matches if m.get("role") == role][:limit]

    if not role_matches:
        st.info(f"No hay partidas de {role} guardadas. Ve a **Partidas** y descarga tu historial.")
        return

    # ── Calcular ──────────────────────────────────────────
    sr = scorer_v2.analyze_player(role_matches, role)
    cr = coaching_engine.analyze_coaching(sr, role_matches, role)
    mx = _compute_metrics(role_matches)

    # ── Layout: 2 columnas principales ────────────────────
    col_main, col_right = st.columns([2.2, 1], gap="medium")

    with col_main:
        # Alerta de sesión
        _render_session_alert(cr.session_warning)

        # Sección 1: Nivel + Tendencia
        _render_level_and_trend(sr, mx)

        # Sección 2: Problema + Plan
        st.markdown('<div class="sec-header"><span class="sec-header-title">⚠️ &nbsp;ANÁLISIS</span></div>', unsafe_allow_html=True)
        c_prob, c_plan = st.columns(2, gap="medium")
        with c_prob:
            _render_problema(cr, mx)
        with c_plan:
            _render_plan(cr)

        # Sección 3: Fortalezas y Debilidades
        st.markdown('<div class="sec-header"><span class="sec-header-title">💪 &nbsp;RENDIMIENTO</span></div>', unsafe_allow_html=True)
        _render_strengths_weaknesses(cr, role)

        # Sección 4: Tendencia
        st.markdown('<div class="sec-header"><span class="sec-header-title">📈 &nbsp;EVOLUCIÓN</span></div>', unsafe_allow_html=True)
        _render_trend_chart(sr, mx, role_matches)

        # Sección 5: Datos avanzados
        st.markdown('<div class="sec-header"><span class="sec-header-title">📊 &nbsp;DATOS AVANZADOS</span></div>', unsafe_allow_html=True)
        st.markdown('<div class="card" style="margin-bottom:1rem">', unsafe_allow_html=True)
        _render_datos_avanzados(mx, sr.benchmarks, role)
        st.markdown('</div>', unsafe_allow_html=True)

        # Sección 6: Champion Intelligence
        cpa = analyze_champion_pool(role_matches, role, sr.match_scores)
        _render_champion_intelligence(cpa)

    with col_right:
        # Objetivo semanal
        _render_objetivo(cr)

        st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)

        # Fortalezas compactas
        st.markdown(
            '<div class="card">'
            '<div class="card-label">💪 &nbsp;TUS FORTALEZAS</div>',
            unsafe_allow_html=True,
        )
        str_icons = ["🛡️", "👥", "🌾"]
        if cr.strengths:
            for i, s in enumerate(cr.strengths):
                st.markdown(
                    f'<div class="str-item">'
                    f'<div class="str-icon">{str_icons[i % 3]}</div>'
                    f'<div>'
                    f'<div class="str-name">{s.name.upper()}</div>'
                    f'<div class="str-evidence">{s.evidence}</div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
        else:
            st.markdown('<p style="font-size:0.78rem;color:#374151">Sin datos suficientes aún.</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)

        # Debilidades compactas
        st.markdown(
            '<div class="card">'
            '<div class="card-label">🔥 &nbsp;TUS DEBILIDADES</div>',
            unsafe_allow_html=True,
        )
        wk_icons = ["💀", "🎯", "📊"]
        main_icon = _problem_icon(cr.primary_problem)
        st.markdown(
            f'<div class="wk-item">'
            f'<div class="wk-icon">{main_icon}</div>'
            f'<div>'
            f'<div class="wk-name">{cr.primary_problem.upper()}</div>'
            f'<div class="wk-evidence">{cr.impact}</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )
        for i, imp in enumerate(cr.improvements):
            st.markdown(
                f'<div class="wk-item">'
                f'<div class="wk-icon">{wk_icons[(i+1)%3]}</div>'
                f'<div>'
                f'<div class="wk-name">{imp.upper()}</div>'
                f'<div class="wk-evidence">{_impact_for(imp, role) or "Área de mejora identificada en tu historial."}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)

        # Resumen de partidas
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
        f'<span style="color:#374151"><b style="color:#4B5563">Acción clave:</b> '
        f'{cr.training_plan.primary}</span>'
        f'<span style="margin-left:auto;color:#1F2937">{conf_str} · N={cr.sample_size} partidas {role}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
