"""
ui/coaching.py — Página de coaching personalizado (Sprint 4).

Estado: infraestructura creada. Contenido pendiente de implementación.
Conectará: scorer_v2.analyze_player() + coaching_engine.analyze_coaching()
"""

import streamlit as st


def render() -> None:
    st.title("🧠 Coaching")
    st.caption("Diagnóstico personalizado basado en tu historial de partidas")
    st.info(
        "**Sprint 4 en construcción.**\n\n"
        "Esta página conectará el motor de coaching con la interfaz. "
        "Cuando esté lista, verás aquí: el problema principal detectado, "
        "el objetivo semanal derivado de tus datos y el plan de entrenamiento."
    )
