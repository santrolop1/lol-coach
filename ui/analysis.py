"""
ui/analysis.py — Página de análisis de rendimiento.

Muestra:
- Score cards promedio (Farm, Survival, Fight, Overall).
- Gráfica de tendencia del Overall Score en las últimas partidas.
- Gráfica de barras comparando los 3 scores.
- Debilidades y fortalezas detectadas.
- Tip prioritario de mejora.
"""

import sys
from pathlib import Path

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

sys.path.insert(0, str(Path(__file__).parent.parent))

import db
from scorer import calculate_score, average_scores
from recommendations import get_recommendations


def _score_color(score: float) -> str:
    if score >= 70:
        return "#4CAF50"   # verde
    if score >= 40:
        return "#FF9800"   # naranja
    return "#F44336"       # rojo


def _score_label(score: float) -> str:
    if score >= 70:
        return "Bueno"
    if score >= 40:
        return "Regular"
    return "Necesita trabajo"


def render() -> None:
    st.title("📊 Análisis de Rendimiento")

    # ----------------------------------------------------------------
    # Verificar configuración
    # ----------------------------------------------------------------
    puuid = db.get_config("puuid")
    if not puuid:
        st.warning("⚠️ Primero configura tu cuenta en **Configuración**.")
        return

    # ----------------------------------------------------------------
    # Filtros
    # ----------------------------------------------------------------
    col1, col2 = st.columns([1, 1])
    with col1:
        role_filter = st.selectbox("Rol", ["Todos", "ADC", "TOP"])
    with col2:
        n_games = st.slider("Últimas partidas", min_value=5, max_value=50, value=20, step=5)

    role_arg = None if role_filter == "Todos" else role_filter
    matches = db.get_matches(puuid, role=role_arg, limit=n_games)
    # Excluir partidas con rol OTHER del análisis
    matches = [m for m in matches if m["role"] in ("ADC", "TOP")]

    if not matches:
        st.info("No hay partidas de ADC o TOP guardadas. Ve a **Partidas** y descarga algunas.")
        return

    # ----------------------------------------------------------------
    # Calcular scores por partida
    # ----------------------------------------------------------------
    scored = [{"match": m, "score": calculate_score(m)} for m in matches]
    avg = average_scores(matches)

    # ----------------------------------------------------------------
    # Score cards promedio
    # ----------------------------------------------------------------
    st.subheader(f"📈 Promedios — últimas {len(matches)} partidas ({role_filter})")

    c1, c2, c3, c4 = st.columns(4)

    def _metric_card(col, label: str, value: float) -> None:
        col.metric(
            label=label,
            value=f"{value:.1f}",
            delta=_score_label(value),
        )

    _metric_card(c1, "🌾 Farm Score",     avg.farm_score)
    _metric_card(c2, "🛡️ Survival Score", avg.survival_score)
    _metric_card(c3, "⚔️ Fight Score",    avg.fight_score)
    _metric_card(c4, "⭐ Overall Score",  avg.overall_score)

    # ----------------------------------------------------------------
    # Gráfica: tendencia del Overall Score
    # ----------------------------------------------------------------
    st.divider()
    st.subheader("📉 Tendencia — Overall Score")

    overall_series = [s["score"].overall_score for s in reversed(scored)]
    dates_series   = [(s["match"]["played_at"] or "")[:10] for s in reversed(scored)]
    labels_series  = [
        f"{s['match']['champion']} ({s['match']['result'][0]})"
        for s in reversed(scored)
    ]

    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=list(range(1, len(overall_series) + 1)),
        y=overall_series,
        mode="lines+markers",
        name="Overall Score",
        line=dict(color="#5B8DEF", width=2),
        marker=dict(
            color=[_score_color(s) for s in overall_series],
            size=8,
        ),
        text=labels_series,
        hovertemplate="Partida %{x}<br>%{text}<br>Score: %{y}<extra></extra>",
    ))
    fig_trend.add_hline(y=70, line_dash="dash", line_color="#4CAF50", annotation_text="Bueno (70)")
    fig_trend.add_hline(y=40, line_dash="dash", line_color="#F44336", annotation_text="Crítico (40)")
    fig_trend.update_layout(
        xaxis_title="Partida (cronológico →)",
        yaxis_title="Score",
        yaxis=dict(range=[0, 105]),
        height=320,
        margin=dict(l=0, r=0, t=10, b=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_trend, use_container_width=True)

    # ----------------------------------------------------------------
    # Gráfica: comparación de los 3 scores
    # ----------------------------------------------------------------
    st.subheader("📊 Desglose de scores promedio")

    score_names  = ["Farm Score", "Survival Score", "Fight Score"]
    score_values = [avg.farm_score, avg.survival_score, avg.fight_score]
    score_colors = [_score_color(v) for v in score_values]

    fig_bar = go.Figure(go.Bar(
        x=score_names,
        y=score_values,
        marker_color=score_colors,
        text=[f"{v:.1f}" for v in score_values],
        textposition="outside",
    ))
    fig_bar.add_hline(y=70, line_dash="dash", line_color="#4CAF50")
    fig_bar.add_hline(y=40, line_dash="dash", line_color="#F44336")
    fig_bar.update_layout(
        yaxis=dict(range=[0, 110]),
        height=280,
        margin=dict(l=0, r=0, t=10, b=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    # ----------------------------------------------------------------
    # Recomendaciones
    # ----------------------------------------------------------------
    st.divider()
    recs = get_recommendations(avg)

    col_weak, col_strong = st.columns(2)

    with col_weak:
        st.subheader("⚠️ Áreas a mejorar")
        if recs.weaknesses:
            for w in recs.weaknesses:
                st.error(w)
        else:
            st.success("¡No hay debilidades críticas! Sigue así.")

    with col_strong:
        st.subheader("✅ Fortalezas")
        if recs.strengths:
            for s in recs.strengths:
                st.success(s)
        else:
            st.info("Aún no hay áreas destacadas. ¡Sigue jugando!")

    if recs.priority_tip:
        st.divider()
        st.subheader("🎯 Objetivo de la semana")
        st.info(recs.priority_tip)

    # ----------------------------------------------------------------
    # Tabla detallada por partida
    # ----------------------------------------------------------------
    with st.expander("Ver detalle por partida"):
        rows = []
        for item in scored:
            m = item["match"]
            s = item["score"]
            rows.append({
                "Fecha":      (m["played_at"] or "")[:10],
                "Campeón":    m["champion"],
                "Rol":        m["role"],
                "Resultado":  "✅" if m["result"] == "WIN" else "❌",
                "KDA":        f"{m['kills']}/{m['deaths']}/{m['assists']}",
                "CS":         m["cs"],
                "Farm":       s.farm_score,
                "Survival":   s.survival_score,
                "Fight":      s.fight_score,
                "Overall":    s.overall_score,
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)
