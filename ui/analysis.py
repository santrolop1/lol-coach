"""
ui/analysis.py — Página de análisis de rendimiento.

Jerarquía visual (orden obligatorio):
  1. Overall Score  — hero principal
  2. Veredicto      — resumen ejecutivo
  3. Problema principal
  4. Objetivo semanal
  5. Acción recomendada
  6. Fortalezas
  7. Debilidades
  8. Gráficas       — Overall Score trend + Muertes trend
  9. Métricas detalladas (expander)
"""

import sys
from pathlib import Path

import streamlit as st
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).parent.parent))

import db
from scorer import calculate_score, average_scores
from recommendations import get_recommendations


# ---------------------------------------------------------------------------
# Constantes de UI (sin tocar la lógica de negocio)
# ---------------------------------------------------------------------------

_SCORE_COLORS = {
    "critical":    "#EF4444",   # 0-39
    "improvement": "#F59E0B",   # 40-59
    "progress":    "#3B82F6",   # 60-79
    "strong":      "#22C55E",   # 80-100
}

_WEAKNESS_META: dict[str, dict] = {
    "farm_score": {
        "title":  "FARMEO DEFICIENTE",
        "causa":  "Estás perdiendo oro acumulado en la fase de líneas.",
        "accion": "Practica 10 minutos de farmeo en partida de práctica antes de rankear.",
    },
    "survival_score": {
        "title":  "DEMASIADAS MUERTES",
        "causa":  "Las muertes tempranas ceden ventaja de oro y presión de mapa.",
        "accion": "Juega conservador cuando no tienes visión del jungler rival.",
    },
    "fight_score": {
        "title":  "BAJO IMPACTO EN PELEAS",
        "causa":  "Podrías llegar tarde a teamfights o morir antes de hacer daño.",
        "accion": "Posiciónate detrás y activa habilidades hacia el grupo rival.",
    },
}

_STRENGTH_META: dict[str, dict] = {
    "farm_score":     {"title": "Buen Farmeo",            "label": "CS/min"},
    "survival_score": {"title": "Buena Supervivencia",    "label": "muertes/partida"},
    "fight_score":    {"title": "Buen Impacto en Peleas", "label": "daño/min"},
}

_WEEKLY_TARGET: dict[str, tuple[str, float]] = {
    "farm_score":     ("CS/min",       7.0),
    "survival_score": ("muertes",      4.0),
    "fight_score":    ("daño/min",   700.0),   # mínimo TOP; ADC usa 900, se ajusta abajo
}

_VEREDICTO: dict[str, str] = {
    "strong":      "Buen rendimiento general. Mantén la consistencia y sigue refinando los detalles.",
    "progress":    "Buen progreso. Hay áreas de mejora claras que puedes atacar esta semana.",
    "improvement": "Hay hábitos que están costando partidas. Corregirlos tendrá impacto directo en tu winrate.",
    "critical":    "Hay problemas críticos afectando tus resultados. Enfócate en una sola área a la vez.",
}


# ---------------------------------------------------------------------------
# Helpers de presentación
# ---------------------------------------------------------------------------

def _score_tier(score: float) -> str:
    if score >= 80: return "strong"
    if score >= 60: return "progress"
    if score >= 40: return "improvement"
    return "critical"


def _score_label(score: float) -> str:
    labels = {
        "strong":      "Strong Performance",
        "progress":    "Good Progress",
        "improvement": "Needs Improvement",
        "critical":    "Critical Issues",
    }
    return labels[_score_tier(score)]


def _chart_layout(height: int = 280) -> dict:
    return dict(
        height=height,
        margin=dict(l=0, r=0, t=10, b=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#94A3B8", size=11),
        xaxis=dict(gridcolor="rgba(128,128,128,0.1)", zeroline=False),
        yaxis=dict(gridcolor="rgba(128,128,128,0.1)", zeroline=False),
    )


def _compute_avgs(matches: list[dict]) -> tuple[float, float, float]:
    """Devuelve (avg_cs_pm, avg_deaths, avg_dmg_pm) del listado de partidas."""
    dur_mins = [max(m["duration_sec"] / 60, 1.0) for m in matches]
    n = len(matches)
    avg_cs_pm  = sum(m["cs"]     / d for m, d in zip(matches, dur_mins)) / n
    avg_deaths = sum(m["deaths"]     for m in matches) / n
    avg_dmg_pm = sum(m["damage"] / d for m, d in zip(matches, dur_mins)) / n
    return avg_cs_pm, avg_deaths, avg_dmg_pm


# ---------------------------------------------------------------------------
# Render principal
# ---------------------------------------------------------------------------

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
    matches  = db.get_matches(puuid, role=role_arg, limit=n_games)
    matches  = [m for m in matches if m["role"] in ("ADC", "TOP")]

    player = db.get_player(puuid)
    if player:
        st.caption(
            f"**{player['riot_id']}#{player['tag']}** · "
            f"Últimas {len(matches)} partidas · {role_filter}"
        )

    # ----------------------------------------------------------------
    # CORRECCIÓN #2 — Estado vacío: menos de 5 partidas
    # ----------------------------------------------------------------
    if len(matches) == 0:
        st.info(
            "No hay partidas de ADC o TOP guardadas. "
            "Ve a **Partidas** y descarga algunas."
        )
        return

    if len(matches) < 5:
        st.info(
            f"Necesitas al menos 5 partidas para generar un análisis confiable. "
            f"Tienes {len(matches)} partida{'s' if len(matches) != 1 else ''}. "
            "Descarga más en **Partidas**."
        )
        return

    # ----------------------------------------------------------------
    # Calcular scores
    # ----------------------------------------------------------------
    scored = [{"match": m, "score": calculate_score(m)} for m in matches]
    avg    = average_scores(matches)

    if avg is None:
        st.error("Error calculando promedios.")
        return

    recs = get_recommendations(avg)

    avg_cs_pm, avg_deaths, avg_dmg_pm = _compute_avgs(matches)

    # Rol primario (para targets de dmg)
    role_counts: dict[str, int] = {}
    for m in matches:
        role_counts[m["role"]] = role_counts.get(m["role"], 0) + 1
    primary_role = max(role_counts, key=role_counts.get)
    dmg_target   = 700.0 if primary_role == "TOP" else 900.0

    # Dimensión con peor score
    score_map = {
        "farm_score":     avg.farm_score,
        "survival_score": avg.survival_score,
        "fight_score":    avg.fight_score,
    }
    lowest_field = min(score_map, key=score_map.get)

    tier  = _score_tier(avg.overall_score)
    color = _SCORE_COLORS[tier]

    # ────────────────────────────────────────────────────────────────
    # 1. OVERALL SCORE — hero
    # ────────────────────────────────────────────────────────────────
    st.markdown(
        f"""
<div class="score-hero fade-in">
    <div class="score-value" style="color:{color}">
        {avg.overall_score:.0f}<span class="score-denom"> / 100</span>
    </div>
    <div class="score-label" style="color:{color}">{_score_label(avg.overall_score)}</div>
</div>
""",
        unsafe_allow_html=True,
    )

    # ────────────────────────────────────────────────────────────────
    # 2. VEREDICTO
    # ────────────────────────────────────────────────────────────────
    st.markdown('<div class="sec-label">Veredicto</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="veredicto fade-in">{_VEREDICTO[tier]}</div>',
        unsafe_allow_html=True,
    )

    # ────────────────────────────────────────────────────────────────
    # 3. PROBLEMA PRINCIPAL  +  4. OBJETIVO SEMANAL  +  5. ACCIÓN
    # (solo si hay priority_tip, i.e. hay algo por mejorar < 65)
    # ────────────────────────────────────────────────────────────────
    if recs.priority_tip:
        meta = _WEAKNESS_META[lowest_field]

        # Objetivo concreto con números reales
        if lowest_field == "farm_score":
            objetivo = f"Aumentar CS/min de {avg_cs_pm:.1f} a 7.0"
        elif lowest_field == "survival_score":
            objetivo = f"Reducir muertes de {avg_deaths:.1f} a 4.0 por partida"
        else:
            objetivo = (
                f"Aumentar daño/min de {avg_dmg_pm:.0f} a "
                f"{int(dmg_target)}"
            )

        # Extraer la acción concreta del priority_tip
        # Formato: "Prioridad esta semana: X. Objetivo concreto: Y. Acción..."
        parts = recs.priority_tip.split(". ")
        accion = ". ".join(parts[2:]) if len(parts) >= 3 else recs.priority_tip

        st.markdown('<div class="sec-label">Prioridad esta semana</div>',
                    unsafe_allow_html=True)

        st.markdown(
            f"""
<div class="obj-card fade-in">
    <div class="oc-label">🎯 Objetivo</div>
    <div class="oc-goal">{objetivo}</div>
    <div class="oc-action">{accion}</div>
</div>
""",
            unsafe_allow_html=True,
        )

    # ────────────────────────────────────────────────────────────────
    # 6. FORTALEZAS
    # ────────────────────────────────────────────────────────────────
    st.markdown('<div class="sec-label">Fortalezas</div>', unsafe_allow_html=True)

    strengths_found = [
        field for field, val in score_map.items() if val >= 70
    ]

    if not strengths_found:
        # CORRECCIÓN #2 — Estado vacío: sin fortalezas
        st.info(
            "Aún no hay patrones positivos claros. "
            "Sigue jugando para obtener más datos."
        )
    else:
        scols = st.columns(len(strengths_found))
        for col, field in zip(scols, strengths_found):
            with col:
                meta  = _STRENGTH_META[field]
                value = score_map[field]
                if field == "farm_score":
                    stat_str = f"{avg_cs_pm:.1f} CS/min"
                elif field == "survival_score":
                    stat_str = f"{avg_deaths:.1f} muertes/partida"
                else:
                    stat_str = f"{avg_dmg_pm:.0f} daño/min"

                st.markdown(
                    f"""
<div class="coach-card strength-card fade-in">
    <div class="cc-label">🏆 {meta['title']}</div>
    <div class="cc-stat" style="color:#F59E0B">{stat_str}</div>
    <div class="cc-body">Score {value:.0f} — por encima del umbral de rendimiento.</div>
</div>
""",
                    unsafe_allow_html=True,
                )

    # ────────────────────────────────────────────────────────────────
    # 7. DEBILIDADES
    # ────────────────────────────────────────────────────────────────
    st.markdown('<div class="sec-label">Áreas a trabajar</div>', unsafe_allow_html=True)

    weaknesses_found = [
        field for field, val in score_map.items() if val < 40
    ]

    if not weaknesses_found:
        # CORRECCIÓN #2 — Estado vacío: sin debilidades críticas
        st.info("No se detectaron problemas críticos. Mantén la consistencia.")
    else:
        for field in weaknesses_found:
            meta  = _WEAKNESS_META[field]
            value = score_map[field]
            if field == "farm_score":
                stat_str = f"{avg_cs_pm:.1f} CS/min promedio"
            elif field == "survival_score":
                stat_str = f"{avg_deaths:.1f} muertes promedio por partida"
            else:
                stat_str = f"{avg_dmg_pm:.0f} daño/min promedio"

            st.markdown(
                f"""
<div class="coach-card weakness-card fade-in">
    <div class="cc-label">{meta['title']}</div>
    <div class="cc-stat" style="color:#EF4444">{stat_str}</div>
    <div class="cc-row cc-cause">Causa probable: {meta['causa']}</div>
    <div class="cc-row cc-action">Acción: {meta['accion']}</div>
</div>
""",
                unsafe_allow_html=True,
            )

    # ────────────────────────────────────────────────────────────────
    # 8. GRÁFICAS
    # ────────────────────────────────────────────────────────────────
    st.markdown('<div class="sec-label">Tendencias</div>', unsafe_allow_html=True)

    # Datos en orden cronológico
    scored_chrono  = list(reversed(scored))
    overall_series = [s["score"].overall_score for s in scored_chrono]
    deaths_series  = [s["match"]["deaths"]      for s in scored_chrono]
    x_axis         = list(range(1, len(scored_chrono) + 1))
    hover_labels   = [
        f"{s['match']['champion']} ({s['match']['result'][0]})"
        for s in scored_chrono
    ]

    col_g1, col_g2 = st.columns(2)

    # — Overall Score trend —
    with col_g1:
        st.markdown("**Overall Score** — evolución")
        fig_overall = go.Figure()
        fig_overall.add_trace(go.Scatter(
            x=x_axis,
            y=overall_series,
            mode="lines+markers",
            name="Overall Score",
            line=dict(color="#3B82F6", width=2),
            marker=dict(
                color=[_SCORE_COLORS[_score_tier(s)] for s in overall_series],
                size=7,
            ),
            text=hover_labels,
            hovertemplate="Partida %{x}<br>%{text}<br>Score: %{y:.0f}<extra></extra>",
        ))
        fig_overall.add_hline(
            y=70, line_dash="dash", line_color="#22C55E",
            annotation_text="Bueno (70)", annotation_position="right",
        )
        fig_overall.add_hline(
            y=40, line_dash="dash", line_color="#EF4444",
            annotation_text="Crítico (40)", annotation_position="right",
        )
        fig_overall.update_layout(
            xaxis_title="Partida →",
            yaxis_title="Score",
            showlegend=False,
            **_chart_layout(280),
        )
        fig_overall.update_yaxes(range=[0, 105])
        st.plotly_chart(fig_overall, width="stretch")

    # — Muertes trend —
    with col_g2:
        st.markdown("**Muertes por partida** — evolución")
        fig_deaths = go.Figure()
        fig_deaths.add_trace(go.Scatter(
            x=x_axis,
            y=deaths_series,
            mode="lines+markers",
            name="Muertes",
            line=dict(color="#EF4444", width=2),
            marker=dict(color="#EF4444", size=7),
            text=hover_labels,
            hovertemplate="Partida %{x}<br>%{text}<br>Muertes: %{y}<extra></extra>",
        ))
        fig_deaths.add_hline(
            y=4, line_dash="dash", line_color="#22C55E",
            annotation_text="Objetivo (4)", annotation_position="right",
        )
        fig_deaths.update_layout(
            xaxis_title="Partida →",
            yaxis_title="Muertes",
            showlegend=False,
            **_chart_layout(280),
        )
        fig_deaths.update_yaxes(range=[0, max(max(deaths_series) + 2, 10)])
        st.plotly_chart(fig_deaths, width="stretch")

    # ────────────────────────────────────────────────────────────────
    # 9. MÉTRICAS DETALLADAS
    # ────────────────────────────────────────────────────────────────
    with st.expander("Ver métricas detalladas por partida"):
        rows = []
        for item in scored:
            m = item["match"]
            s = item["score"]
            dur_min = m["duration_sec"] // 60
            dur_sec = m["duration_sec"] % 60
            rows.append({
                "Fecha":    (m["played_at"] or "")[:10],
                "Campeón":  m["champion"],
                "Rol":      m["role"],
                "Resultado": "✅" if m["result"] == "WIN" else "❌",
                "KDA":      f"{m['kills']}/{m['deaths']}/{m['assists']}",
                "CS/min":   round(m["cs"] / max(m["duration_sec"] / 60, 1), 1),
                "Daño":     m["damage"],
                "Duración": f"{dur_min}m {dur_sec:02d}s",
                "Farm":     s.farm_score,
                "Superv.":  s.survival_score,
                "Pelea":    s.fight_score,
                "Overall":  s.overall_score,
            })

        st.dataframe(rows, width="stretch", hide_index=True)

        # Promedios de los 3 sub-scores al final de la tabla
        st.caption(
            f"Promedios — Farm: {avg.farm_score:.1f} · "
            f"Supervivencia: {avg.survival_score:.1f} · "
            f"Pelea: {avg.fight_score:.1f} · "
            f"Overall: {avg.overall_score:.1f}"
        )
