"""
analytics.py — Instrumentación local mínima (Sprint 2).

Envuelve db.log_event() con manejo de sesión de Streamlit. Solo escribe a
SQLite local — nunca se conecta a internet. No registra datos personales
(ni riot_id, ni puuid, ni api_key); los nombres de campeón no son datos
personales.

Limitación conocida: si el usuario cierra la app sin cambiar de pantalla,
el tiempo en la última pantalla no se registra (Streamlit no expone un
hook de cierre de sesión sin JS adicional). La duración total de sesión se
deriva del rango de timestamps en event_log por session_id, no de un
evento explícito de cierre.
"""

import time
import uuid

import streamlit as st

import db


def get_session_id() -> str:
    """ID de sesión aleatorio, generado una vez por sesión de Streamlit."""
    if "analytics_session_id" not in st.session_state:
        st.session_state["analytics_session_id"] = uuid.uuid4().hex
        db.log_event(st.session_state["analytics_session_id"], "session_start")
    return st.session_state["analytics_session_id"]


def track_screen(screen: str) -> None:
    """
    Registra apertura de pantalla y el tiempo pasado en la pantalla anterior.
    Llamar una vez al inicio del render() de cada página.
    """
    session_id = get_session_id()
    now = time.monotonic()

    prev_screen     = st.session_state.get("analytics_current_screen")
    prev_entered_at = st.session_state.get("analytics_screen_entered_at")

    if prev_screen is not None and prev_screen != screen and prev_entered_at is not None:
        db.log_event(
            session_id, "screen_time", screen=prev_screen,
            payload={"seconds": round(now - prev_entered_at, 1)},
        )

    if prev_screen != screen:
        db.log_event(session_id, "screen_open", screen=screen)
        st.session_state["analytics_current_screen"]    = screen
        st.session_state["analytics_screen_entered_at"] = now


def track_event(event_type: str, screen: str | None = None, payload: dict | None = None) -> None:
    db.log_event(get_session_id(), event_type, screen=screen, payload=payload)
