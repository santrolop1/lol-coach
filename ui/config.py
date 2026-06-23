"""
ui/config.py — Centro de cuenta post-onboarding.

Permite al usuario ver su perfil, actualizar la API Key,
sincronizar partidas y gestionar sus datos.
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

PLATFORM_NAMES = {v: k for k, v in PLATFORMS.items()}

QUEUE_OPTIONS = {
    "Ranked Solo/Duo": 420,
    "Normal Draft":    400,
    "Todas":           0,
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _stat_card(label: str, value: str, sub: str = "") -> str:
    return (
        f'<div class="cfg-stat">'
        f'  <div class="cfg-stat-val">{value}</div>'
        f'  <div class="cfg-stat-lbl">{label}</div>'
        f'  {"<div class=\"cfg-stat-sub\">" + sub + "</div>" if sub else ""}'
        f'</div>'
    )


def _section(title: str) -> None:
    st.markdown(
        f'<div class="sec-header"><span class="sec-header-title">{title}</span></div>',
        unsafe_allow_html=True,
    )


# ── Secciones ─────────────────────────────────────────────────────────────────

def _render_account(puuid: str) -> None:
    _section("👤 &nbsp;CUENTA RIOT")

    player   = db.get_player(puuid)
    platform = db.get_config("platform") or "la1"
    region   = PLATFORM_NAMES.get(platform, platform.upper())

    if player:
        total = player.get("wins", 0) + player.get("losses", 0)
        wr_str = (
            f"{round(player['wins'] / total * 100, 0):.0f}% WR"
            if total > 0 else "—"
        )

        st.markdown(
            f'<div class="player-card fade-in">'
            f'  <div class="pc-name">✅ &nbsp;{player["riot_id"]}#{player["tag"]}</div>'
            f'  <div class="pc-meta">'
            f'    Nivel {player.get("level", "?")} &nbsp;·&nbsp; '
            f'    {player.get("rank", "Sin rango")} &nbsp;·&nbsp; '
            f'    {player.get("lp", 0)} LP &nbsp;·&nbsp; {wr_str}'
            f'  </div>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div style="font-size:0.78rem;color:#6B7280;margin-bottom:1.25rem">'
            f'Servidor: {region} &nbsp;·&nbsp; PUUID: {puuid[:12]}…'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.info("No se encontraron datos del perfil.")

    with st.expander("🔧 Cambiar cuenta o región"):
        _render_change_account_form()


def _render_api_section() -> None:
    _section("🔑 &nbsp;API KEY")

    api_key = db.get_config("api_key") or ""
    masked  = f"RGAPI-{'*' * 8}-…-{api_key[-6:]}" if len(api_key) > 10 else "(no configurada)"

    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(
            f'<div style="font-size:0.85rem;color:#D1D5DB;padding:0.75rem 0">'
            f'{masked}</div>',
            unsafe_allow_html=True,
        )
    with col2:
        if api_key:
            st.markdown(
                '<div style="font-size:0.75rem;color:#22C55E;padding:0.82rem 0">● Configurada</div>',
                unsafe_allow_html=True,
            )

    new_key = st.text_input(
        "Nueva API Key",
        type="password",
        placeholder="RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        key="cfg_new_api_key",
    )

    if st.button("Actualizar API Key", key="cfg_save_key"):
        if not new_key.strip():
            st.error("La clave no puede estar vacía.")
        else:
            platform = db.get_config("platform") or "la1"
            with st.spinner("Verificando..."):
                try:
                    ok = setup_service.validate_api_key(new_key.strip(), platform)
                except Exception:
                    ok = False

            if ok:
                db.save_config("api_key", new_key.strip())
                st.success("✅ API Key actualizada y verificada.")
                st.rerun()
            else:
                st.error("API Key inválida o expirada.")

    st.caption(
        "Las Dev Keys de Riot expiran cada 24 h. "
        "Actualízala aquí sin perder tus partidas guardadas."
    )


def _render_data_section(puuid: str) -> None:
    _section("📊 &nbsp;DATOS")

    n_total = setup_service.count_matches()
    n_adc   = setup_service.count_matches("ADC")
    n_top   = setup_service.count_matches("TOP")
    last_sync = setup_service.last_sync_date() or "—"

    st.markdown(
        f'<div class="cfg-stat-row">'
        f'  {_stat_card("Total", str(n_total), "partidas")}'
        f'  {_stat_card("ADC", str(n_adc), "partidas")}'
        f'  {_stat_card("TOP", str(n_top), "partidas")}'
        f'  {_stat_card("Última sync", last_sync)}'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div style="margin-top:1.25rem"></div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        queue_label = st.selectbox(
            "Tipo de partida",
            options=list(QUEUE_OPTIONS.keys()),
            key="cfg_queue",
        )
        count_opts = {"20 partidas": 20, "50 partidas": 50}
        count_label = st.selectbox(
            "Cantidad",
            options=list(count_opts.keys()),
            key="cfg_count",
        )

    with col2:
        st.markdown('<div style="height:4.2rem"></div>', unsafe_allow_html=True)
        if st.button("🔄 Sincronizar partidas", use_container_width=True, type="primary", key="cfg_sync"):
            _do_sync(puuid, count_opts[count_label], QUEUE_OPTIONS[queue_label])

    st.markdown('<div style="margin-top:0.5rem"></div>', unsafe_allow_html=True)
    if st.button("🔃 Reanalizar perfil", use_container_width=True, key="cfg_reanalyze"):
        for key in list(st.session_state.keys()):
            if key.startswith("cpa_") or key.startswith("champ_"):
                del st.session_state[key]
        st.success("✅ Caché limpiado. El análisis se regenerará automáticamente.")


def _do_sync(puuid: str, count: int, queue: int) -> None:
    api_key  = db.get_config("api_key") or ""
    platform = db.get_config("platform") or "la1"

    if not api_key:
        st.error("Configura una API Key antes de sincronizar.")
        return

    progress_bar = st.progress(0, text="Iniciando sincronización...")
    status_empty = st.empty()

    def _on_progress(done: int, total: int) -> None:
        progress_bar.progress(done / max(total, 1), text=f"Descargando {done}/{total}...")

    try:
        result = setup_service.download_matches(
            puuid=puuid, api_key=api_key, platform=platform,
            count=count, queue=queue, on_progress=_on_progress,
        )
        progress_bar.empty()
        status_empty.empty()

        if result["total_new"] == 0:
            st.info(f"✅ Ya tienes las partidas más recientes ({result['already_saved']} guardadas).")
        else:
            st.success(
                f"✅ {result['saved']} partidas nuevas guardadas · "
                f"{result['skipped']} omitidas."
            )
        st.rerun()

    except RiotAPIError as e:
        progress_bar.empty()
        status_empty.empty()
        st.error(f"Error al sincronizar: {e}")


def _render_change_account_form() -> None:
    saved_key      = db.get_config("api_key")      or ""
    saved_name     = db.get_config("game_name")    or ""
    saved_tag      = db.get_config("tag_line")     or ""
    saved_platform = db.get_config("platform")     or "la1"

    platform_labels = list(PLATFORMS.keys())
    platform_values = list(PLATFORMS.values())
    default_idx = (
        platform_values.index(saved_platform)
        if saved_platform in platform_values else 0
    )

    with st.form("cfg_change_account_form"):
        api_key = st.text_input(
            "API Key",
            value=saved_key,
            type="password",
            placeholder="RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        )
        col1, col2 = st.columns([3, 1])
        with col1:
            game_name = st.text_input(
                "Nombre de invocador",
                value=saved_name,
                placeholder="NombreEjemplo",
            )
        with col2:
            tag_line = st.text_input("Tag", value=saved_tag, placeholder="LA1")

        platform_label = st.selectbox(
            "Servidor",
            options=platform_labels,
            index=default_idx,
        )

        submitted = st.form_submit_button(
            "Actualizar y verificar",
            use_container_width=True,
            type="primary",
        )

    if not submitted:
        return

    errors = []
    if not api_key.strip():   errors.append("La API Key no puede estar vacía.")
    if not game_name.strip(): errors.append("El nombre no puede estar vacío.")
    if not tag_line.strip():  errors.append("El tag no puede estar vacío.")
    for e in errors:
        st.error(e)
    if errors:
        return

    platform = PLATFORMS[platform_label]

    with st.spinner("Verificando cuenta..."):
        try:
            profile = setup_service.resolve_riot_account(
                api_key.strip(), platform, game_name.strip(), tag_line.strip()
            )
            setup_service.save_account(
                api_key.strip(), platform, game_name.strip(), tag_line.strip(), profile
            )
        except RiotNotFoundError:
            st.error(
                f"No se encontró la cuenta {game_name.strip()}#{tag_line.strip()}."
            )
            return
        except RiotAPIError as e:
            st.error(f"Error de API: {e}")
            return

    st.success(f"✅ Cuenta actualizada: {profile['riot_id']}#{profile['tag']}")
    st.rerun()


# ── Render principal ──────────────────────────────────────────────────────────

def render() -> None:
    st.title("⚙️ Configuración")

    puuid = db.get_config("puuid")
    if not puuid:
        st.warning("⚠️ Sin cuenta configurada. Completa el setup inicial.")
        return

    _render_account(puuid)
    st.divider()
    _render_api_section()
    st.divider()
    _render_data_section(puuid)
