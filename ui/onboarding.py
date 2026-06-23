"""
ui/onboarding.py — Flujo obligatorio de configuración inicial.

Bloquea el acceso a la app hasta que el setup esté completo.
4 pasos: API Key → Cuenta Riot → Descarga de partidas → Listo.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

import db
from backend.services import setup_service
from riot_api import RiotAPIError, RiotNotFoundError

PLATFORMS = {
    "Latinoamérica Norte (LA1)": "la1",
    "Latinoamérica Sur (LA2)":   "la2",
    "Norteamérica (NA1)":        "na1",
    "Europa Oeste (EUW1)":       "euw1",
    "Europa Norte/Este (EUN1)":  "eun1",
    "Brasil (BR1)":              "br1",
    "Corea (KR)":                "kr",
    "Japón (JP1)":               "jp1",
    "Oceanía (OC1)":             "oc1",
}


# ── Helpers de UI ─────────────────────────────────────────────────────────────

def _step_bar(current: int) -> str:
    labels = ["API Key", "Tu cuenta", "Partidas", "Listo"]
    items  = ""
    for i, label in enumerate(labels, 1):
        if i < current:
            state = "done"
            dot   = "✓"
        elif i == current:
            state = "active"
            dot   = str(i)
        else:
            state = ""
            dot   = str(i)
        items += (
            f'<div class="ob-step {state}">'
            f'  <div class="ob-step-dot">{dot}</div>'
            f'  <div class="ob-step-label">{label}</div>'
            f'</div>'
        )
    return f'<div class="ob-steps">{items}</div>'


def _success_box(text: str) -> None:
    st.markdown(
        f'<div class="ob-success">✓ &nbsp;{text}</div>',
        unsafe_allow_html=True,
    )


def _error_box(text: str) -> None:
    st.markdown(
        f'<div class="ob-error">✕ &nbsp;{text}</div>',
        unsafe_allow_html=True,
    )


def _account_preview(profile: dict) -> None:
    wr_str = ""
    total = profile.get("wins", 0) + profile.get("losses", 0)
    if total > 0:
        wr    = round(profile["wins"] / total * 100, 0)
        wr_str = f" · {int(wr)}% WR ({total}P)"
    st.markdown(
        f'<div class="ob-account-preview">'
        f'  <div class="ob-account-icon">👤</div>'
        f'  <div>'
        f'    <div class="ob-account-name">{profile["riot_id"]}#{profile["tag"]}</div>'
        f'    <div class="ob-account-meta">Nivel {profile["level"]}{wr_str}</div>'
        f'  </div>'
        f'  <div class="ob-account-rank">{profile["rank"]}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Steps ─────────────────────────────────────────────────────────────────────

def _step1_api_key() -> None:
    st.markdown(
        '<div class="ob-card-title">Conecta tu API Key de Riot</div>'
        '<div class="ob-card-sub">'
        'Necesitamos tu clave para acceder al historial de tus partidas.<br>'
        'Obtén una clave gratuita (30 segundos) en '
        '<a href="https://developer.riotgames.com" target="_blank" style="color:#8B5CF6">'
        'developer.riotgames.com</a>.'
        '</div>',
        unsafe_allow_html=True,
    )

    platform_labels  = list(PLATFORMS.keys())
    platform_values  = list(PLATFORMS.values())
    saved_platform   = db.get_config("platform") or "la1"
    default_idx      = platform_values.index(saved_platform) if saved_platform in platform_values else 0
    saved_key        = db.get_config("api_key") or ""

    api_key = st.text_input(
        "API Key",
        value=saved_key,
        type="password",
        placeholder="RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        key="ob_api_key_input",
    )
    platform_label = st.selectbox(
        "Región de tu servidor",
        options=platform_labels,
        index=default_idx,
        key="ob_platform_select",
    )

    if st.button("Verificar API Key →", use_container_width=True, type="primary", key="ob_btn_step1"):
        if not api_key.strip():
            _error_box("Ingresa tu API Key antes de continuar.")
            return

        with st.spinner("Verificando API Key..."):
            try:
                ok = setup_service.validate_api_key(api_key.strip(), PLATFORMS[platform_label])
            except Exception:
                ok = False

        if ok:
            st.session_state.ob_api_key  = api_key.strip()
            st.session_state.ob_platform = PLATFORMS[platform_label]
            st.session_state.ob_step     = 2
            st.rerun()
        else:
            _error_box("API Key inválida o expirada. Las Dev Keys se renuevan cada 24 h.")


def _step2_riot_id() -> None:
    api_key  = st.session_state.ob_api_key
    platform = st.session_state.ob_platform

    _success_box("API Key verificada")
    st.markdown(
        '<div class="ob-card-title">Ingresa tu Riot ID</div>'
        '<div class="ob-card-sub">'
        'El nombre que aparece en el cliente de League of Legends, separado por #.'
        '</div>',
        unsafe_allow_html=True,
    )

    saved_name = db.get_config("game_name") or ""
    saved_tag  = db.get_config("tag_line")  or ""

    col1, col2 = st.columns([3, 1])
    with col1:
        game_name = st.text_input(
            "Nombre de invocador",
            value=saved_name,
            placeholder="KBTZASK8",
            key="ob_game_name",
        )
    with col2:
        tag_line = st.text_input(
            "Tag",
            value=saved_tag,
            placeholder="9829",
            key="ob_tag_line",
        )

    if st.button("Buscar cuenta →", use_container_width=True, type="primary", key="ob_btn_step2"):
        if not game_name.strip() or not tag_line.strip():
            _error_box("Completa el nombre y el tag.")
            return

        with st.spinner("Buscando cuenta..."):
            try:
                profile = setup_service.resolve_riot_account(
                    api_key, platform, game_name.strip(), tag_line.strip()
                )
                setup_service.save_account(
                    api_key, platform, game_name.strip(), tag_line.strip(), profile
                )
                st.session_state.ob_account = profile
                st.session_state.ob_step    = 3
                st.rerun()
            except RiotNotFoundError:
                _error_box(f"Cuenta {game_name.strip()}#{tag_line.strip()} no encontrada. Revisa el nombre y tag.")
            except RiotAPIError as e:
                _error_box(f"Error de API: {e}")


def _step3_download() -> None:
    account  = st.session_state.ob_account
    api_key  = st.session_state.ob_api_key
    platform = st.session_state.ob_platform

    _success_box("Cuenta verificada")
    _account_preview(account)

    st.markdown(
        '<div class="ob-card-title">Descarga tus partidas</div>'
        '<div class="ob-card-sub">'
        'Necesitamos tu historial para generar tu análisis personalizado. '
        'El análisis mejora con más partidas.'
        '</div>',
        unsafe_allow_html=True,
    )

    count_opts = {"20 partidas (rápido)": 20, "50 partidas (recomendado)": 50}
    count_label = st.selectbox(
        "¿Cuántas partidas descargar?",
        options=list(count_opts.keys()),
        index=1,
        key="ob_count_select",
    )

    queue_opts = {
        "Ranked Solo/Duo": 420,
        "Normal Draft":    400,
        "Todas":           0,
    }
    queue_label = st.selectbox(
        "Tipo de partida",
        options=list(queue_opts.keys()),
        key="ob_queue_select",
    )

    if st.button("Descargar partidas →", use_container_width=True, type="primary", key="ob_btn_step3"):
        count = count_opts[count_label]
        queue = queue_opts[queue_label]

        progress_bar  = st.progress(0, text="Iniciando descarga...")
        status_text   = st.empty()

        def _on_progress(done: int, total: int) -> None:
            pct  = done / max(total, 1)
            text = f"Descargando {done}/{total}..."
            progress_bar.progress(pct, text=text)
            status_text.markdown(
                f'<div style="font-size:0.8rem;color:#9CA3AF;text-align:center">'
                f'{done} / {total} partidas procesadas</div>',
                unsafe_allow_html=True,
            )

        try:
            with st.spinner(""):
                result = setup_service.download_matches(
                    puuid      = account["puuid"],
                    api_key    = api_key,
                    platform   = platform,
                    count      = count,
                    queue      = queue,
                    on_progress = _on_progress,
                )

            progress_bar.empty()
            status_text.empty()

            if result["total_new"] == 0 and result["already_saved"] > 0:
                _success_box(f"Ya tienes las partidas más recientes ({result['already_saved']} guardadas).")
            else:
                _success_box(
                    f"{result['saved']} partidas nuevas guardadas · "
                    f"{result['skipped']} de otro rol / ya existentes."
                )

            st.session_state.ob_step = 4
            st.rerun()

        except RiotAPIError as e:
            progress_bar.empty()
            status_text.empty()
            _error_box(f"Error al descargar partidas: {e}")


def _step4_ready() -> None:
    account = st.session_state.get("ob_account") or {}
    n = setup_service.count_matches()

    st.markdown(
        '<div style="text-align:center;padding:1.5rem 0">'
        '<div style="font-size:2.5rem;margin-bottom:1rem">🎉</div>'
        '<div class="ob-card-title" style="font-size:1.2rem;text-align:center">¡Listo para entrenar!</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    if account:
        _account_preview(account)

    st.markdown(
        f'<div style="font-size:0.85rem;color:#9CA3AF;text-align:center;margin:0.75rem 0 1.5rem">'
        f'{n} partidas analizadas · Tu perfil está listo.'
        f'</div>',
        unsafe_allow_html=True,
    )

    if st.button("Entrar a LoL Coach →", use_container_width=True, type="primary", key="ob_btn_done"):
        # Limpiar estado de onboarding
        for k in ["ob_step", "ob_api_key", "ob_platform", "ob_account"]:
            st.session_state.pop(k, None)
        st.rerun()


# ── Render principal ──────────────────────────────────────────────────────────

def render() -> None:
    """
    Renderiza el flujo de onboarding.
    Bloquea el acceso a la app hasta que setup esté completo.
    """
    if "ob_step" not in st.session_state:
        st.session_state.ob_step = 1

    step = st.session_state.ob_step

    # Columna centrada
    _, col, _ = st.columns([1, 2.2, 1])
    with col:
        # Logo
        st.markdown(
            '<div class="ob-logo">'
            '  <div class="ob-logo-icon">⚡</div>'
            '  <div class="ob-logo-title">LOL COACH</div>'
            '  <div class="ob-logo-sub">Tu mejor versión</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        # Barra de pasos
        st.markdown(_step_bar(step), unsafe_allow_html=True)

        # Contenido del paso actual
        st.markdown('<div class="ob-card">', unsafe_allow_html=True)

        if step == 1:
            _step1_api_key()
        elif step == 2:
            _step2_riot_id()
        elif step == 3:
            _step3_download()
        elif step == 4:
            _step4_ready()

        st.markdown('</div>', unsafe_allow_html=True)
