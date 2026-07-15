"""
ui/about.py — Pantalla "Acerca de" y herramientas de diagnóstico para beta.

Facilita el soporte durante la beta: los testers pueden exportar su
diagnóstico completo con un botón y enviarlo al desarrollador.
"""

from __future__ import annotations

import json
import platform
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

import _paths
import db
from backend.version import APP_NAME, VERSION, SUPPORT_EMAIL, GITHUB_REPO


# ── Helpers ───────────────────────────────────────────────────────────────────

def _collect_diagnostic() -> dict:
    """Construye el objeto de diagnóstico completo."""
    info: dict = {
        "timestamp":    datetime.now(timezone.utc).isoformat(),
        "app_version":  VERSION,
        "python":       sys.version,
        "platform":     platform.platform(),
        "frozen":       getattr(sys, "frozen", False),
        "data_dir":     str(_paths.get_data_dir()),
        "cache_dir":    str(_paths.get_cache_dir()),
        "db_exists":    _paths.get_data_dir().joinpath("lol_coach.db").exists(),
        "db_size_kb":   None,
        "config":       {},
        "match_count":  0,
        "errors":       [],
    }

    db_path = _paths.get_data_dir() / "lol_coach.db"
    if db_path.exists():
        info["db_size_kb"] = round(db_path.stat().st_size / 1024, 1)
        try:
            conn = sqlite3.connect(str(db_path))
            info["match_count"] = conn.execute("SELECT COUNT(*) FROM match").fetchone()[0]

            safe_keys = ["game_name", "tag_line", "platform", "puuid"]
            for k in safe_keys:
                val = db.get_config(k)
                info["config"][k] = val if val else "(no configurado)"
            conn.close()
        except Exception as e:
            info["errors"].append(f"DB read error: {e}")

    log_dir = _paths.get_log_dir()
    log_files = sorted(log_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)[:3]
    info["recent_logs"] = [p.name for p in log_files]

    return info


def _last_logs(n: int = 100) -> str:
    """Últimas n líneas de logs disponibles."""
    log_dir = _paths.get_log_dir()
    log_files = sorted(log_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not log_files:
        return "(no hay archivos de log)"
    lines = log_files[0].read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-n:])


# ── Página principal ──────────────────────────────────────────────────────────

def render() -> None:
    st.title(f"ℹ️ {APP_NAME}")

    # Versión
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(f"**Versión:** `{VERSION}`")
        st.markdown(f"**Python:** `{sys.version.split()[0]}`")
        st.markdown(f"**Sistema:** `{platform.system()} {platform.release()}`")
    with col2:
        frozen = getattr(sys, "frozen", False)
        st.metric("Modo", "Instalado" if frozen else "Desarrollo")
    with col3:
        db_ok = _paths.get_data_dir().joinpath("lol_coach.db").exists()
        st.metric("Base de datos", "✓ OK" if db_ok else "✗ No encontrada")

    st.divider()

    # ── Diagnóstico ───────────────────────────────────────────────────────────
    st.subheader("🔍 Diagnóstico")

    if st.button("Exportar diagnóstico completo", type="primary"):
        diag = _collect_diagnostic()
        diag_json = json.dumps(diag, indent=2, ensure_ascii=False)
        st.download_button(
            label="⬇️ Descargar diagnóstico.json",
            data=diag_json,
            file_name=f"lol_coach_diagnostico_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
        )

        with st.expander("Ver diagnóstico", expanded=True):
            st.json(diag)

    st.divider()

    # ── Logs ──────────────────────────────────────────────────────────────────
    st.subheader("📋 Logs recientes")

    if st.button("Cargar últimos logs"):
        logs = _last_logs(150)
        st.code(logs, language="text")
        st.download_button(
            label="⬇️ Descargar logs",
            data=logs,
            file_name=f"lol_coach_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
        )

    st.divider()

    # ── Reportar error ────────────────────────────────────────────────────────
    st.subheader("🐛 Reportar un error")

    st.markdown(
        f"Si encontraste un problema, exporta el diagnóstico arriba y envíalo por:"
    )

    col_a, col_b = st.columns(2)
    with col_a:
        st.link_button("📝 Abrir Issue en GitHub", f"{GITHUB_REPO}/issues/new")
    with col_b:
        st.link_button("📧 Enviar por Email", f"mailto:{SUPPORT_EMAIL}?subject=Bug%20LoL%20Coach%20{VERSION}")

    st.divider()

    # ── Rutas del sistema ─────────────────────────────────────────────────────
    with st.expander("📁 Rutas del sistema"):
        st.code(
            f"Datos:   {_paths.get_data_dir()}\n"
            f"Caché:   {_paths.get_cache_dir()}\n"
            f"Logs:    {_paths.get_log_dir()}\n"
            f"Bundle:  {_paths.get_bundle_dir()}",
            language="text",
        )
