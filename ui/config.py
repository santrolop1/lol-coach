"""
ui/config.py — Página de configuración con flujo de onboarding.
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

import db
from riot_api import RiotClient, RiotAPIError, RiotNotFoundError


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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _step_html(s1: str, s2: str, s3: str, s4: str) -> str:
    """Renderiza el indicador de 4 pasos. Cada argumento: 'pending'|'active'|'done'."""
    labels = ["Conecta Riot", "Verifica cuenta", "Descarga partidas", "Analiza"]
    icons  = ["①", "②", "③", "④"]
    states = [s1, s2, s3, s4]
    items = ""
    for icon, label, state in zip(icons, labels, states):
        items += (
            f'<div class="step-item {state}">'
            f'<span class="step-num">{icon}</span>{label}'
            f"</div>"
        )
    return f'<div class="steps fade-in">{items}</div>'


def _player_card_html(name: str, tag: str, level: int, rank: str, lp: int) -> str:
    return f"""
<div class="player-card fade-in">
    <div class="pc-name">✅ &nbsp;{name}#{tag}</div>
    <div class="pc-meta">
        Nivel {level} &nbsp;·&nbsp; {rank} &nbsp;·&nbsp; {lp} LP
    </div>
</div>
"""


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render() -> None:
    st.title("⚙️ Configuración")

    puuid        = db.get_config("puuid")
    is_verified  = bool(puuid)

    # Determinar estado de partidas para indicador de pasos
    n_matches = 0
    if is_verified and puuid:
        n_matches = len(db.get_matches(puuid, limit=1))

    # ----------------------------------------------------------------
    # Indicador de pasos
    # ----------------------------------------------------------------
    if not is_verified:
        st.markdown(_step_html("active", "pending", "pending", "pending"),
                    unsafe_allow_html=True)
    elif n_matches == 0:
        st.markdown(_step_html("done", "done", "active", "pending"),
                    unsafe_allow_html=True)
    else:
        st.markdown(_step_html("done", "done", "done", "active"),
                    unsafe_allow_html=True)

    # ----------------------------------------------------------------
    # Estado A: cuenta NO verificada → mostrar formulario
    # ----------------------------------------------------------------
    if not is_verified:
        _render_form()
        return

    # ----------------------------------------------------------------
    # Estado B: cuenta verificada → mostrar perfil + next steps
    # ----------------------------------------------------------------
    player = db.get_player(puuid) if puuid else None

    if player:
        st.markdown(
            _player_card_html(
                player["riot_id"],
                player["tag"],
                player.get("level", 0),
                player.get("rank", "Sin rango"),
                player.get("lp", 0),
            ),
            unsafe_allow_html=True,
        )
    else:
        st.success("✅ Cuenta conectada.")

    # Next steps
    st.markdown('<div class="sec-label">Siguientes pasos</div>', unsafe_allow_html=True)

    step3_class = "done" if n_matches > 0 else "current"
    step4_class = "done" if n_matches > 0 else "ns-item"

    st.markdown(
        f"""
<div class="next-steps fade-in">
    <div class="ns-item done">✅ &nbsp; Conecta tu cuenta de Riot</div>
    <div class="ns-item done">✅ &nbsp; Verifica tu identidad</div>
    <div class="ns-item {step3_class}">
        {'✅' if n_matches > 0 else '→'} &nbsp; Descarga tus partidas
    </div>
    <div class="ns-item">
        {'✅' if n_matches > 0 else '·'} &nbsp; Analiza tu rendimiento
    </div>
</div>
""",
        unsafe_allow_html=True,
    )

    if n_matches == 0:
        st.info(
            "Descarga al menos 5 partidas para generar tu primer análisis. "
            "Ve a **Partidas** en el menú lateral."
        )
        if st.button("→ Ir a Partidas", key="cta_go_matches"):
            st.session_state.current_page = "🎮 Partidas"
            st.rerun()
    else:
        if st.button("→ Ver mi análisis", key="cta_go_analysis"):
            st.session_state.current_page = "📊 Análisis"
            st.rerun()

    # ----------------------------------------------------------------
    # Sección de mantenimiento (API Key, cambiar cuenta)
    # ----------------------------------------------------------------
    st.divider()

    with st.expander("🔑 Actualizar API Key"):
        st.caption(
            "La Dev Key de Riot expira cada 24h. "
            "Actualízala aquí sin perder tus partidas descargadas."
        )
        saved_key = db.get_config("api_key") or ""
        new_key = st.text_input(
            "Nueva API Key",
            value=saved_key,
            type="password",
            placeholder="RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            key="update_api_key",
        )
        if st.button("Guardar API Key", key="save_api_key_btn"):
            if not new_key.strip():
                st.error("La clave no puede estar vacía.")
            else:
                db.save_config("api_key", new_key.strip())
                st.success("✅ API Key actualizada.")

    with st.expander("🔧 Cambiar cuenta o región"):
        _render_form(compact=True)


# ---------------------------------------------------------------------------
# Formulario de configuración
# ---------------------------------------------------------------------------

def _render_form(compact: bool = False) -> None:
    saved_key      = db.get_config("api_key")      or ""
    saved_name     = db.get_config("game_name")    or ""
    saved_tag      = db.get_config("tag_line")     or ""
    saved_platform = db.get_config("platform")     or "la1"

    platform_labels  = list(PLATFORMS.keys())
    platform_values  = list(PLATFORMS.values())
    default_idx = (
        platform_values.index(saved_platform)
        if saved_platform in platform_values else 0
    )

    form_key = "config_form_compact" if compact else "config_form_main"

    if not compact:
        st.markdown(
            "Conecta tu cuenta de Riot Games para empezar a entrenar.",
            help=None,
        )
        st.markdown("")

    with st.form(form_key):
        if not compact:
            st.markdown("**🔑 API Key de Riot Developer**")
            st.caption(
                "Obtén tu clave gratuita en [developer.riotgames.com](https://developer.riotgames.com).  \n"
                "La Dev Key expira cada 24h — recuérdala regenerar."
            )
        api_key = st.text_input(
            "API Key",
            value=saved_key,
            type="password",
            placeholder="RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        )

        if not compact:
            st.markdown("")
            st.markdown("**👤 Tu Riot ID**")

        col1, col2 = st.columns([3, 1])
        with col1:
            game_name = st.text_input(
                "Nombre de invocador",
                value=saved_name,
                placeholder="NombreEjemplo",
            )
        with col2:
            tag_line = st.text_input(
                "Tag",
                value=saved_tag,
                placeholder="LA1",
            )

        if not compact:
            st.markdown("**🌍 Región**")
        platform_label = st.selectbox(
            "Servidor",
            options=platform_labels,
            index=default_idx,
        )

        label_btn = "Guardar y verificar cuenta" if not compact else "Actualizar y verificar"
        submitted = st.form_submit_button(
            f"→ {label_btn}",
            use_container_width=True,
            type="primary",
        )

    if not submitted:
        return

    # Validaciones
    errors = []
    if not api_key.strip():
        errors.append("La API Key no puede estar vacía.")
    if not game_name.strip():
        errors.append("El nombre de invocador no puede estar vacío.")
    if not tag_line.strip():
        errors.append("El tag no puede estar vacío.")

    if errors:
        for e in errors:
            st.error(e)
        return

    platform = PLATFORMS[platform_label]

    # Guardar en DB
    db.save_config("api_key",   api_key.strip())
    db.save_config("game_name", game_name.strip())
    db.save_config("tag_line",  tag_line.strip().lstrip("#"))
    db.save_config("platform",  platform)

    # Verificar con Riot API
    with st.spinner("Conectando con Riot API..."):
        try:
            client  = RiotClient(api_key.strip(), platform)
            account = client.get_account(game_name.strip(), tag_line.strip().lstrip("#"))
            summoner = client.get_summoner(account["puuid"])
            league_entries = client.get_league_by_puuid(account["puuid"])

            solo_entry = next(
                (e for e in league_entries if e.get("queueType") == "RANKED_SOLO_5x5"),
                None,
            )

            rank_str  = "Sin rango"
            tier_str  = ""
            lp = wins = losses = 0
            if solo_entry:
                tier_str = solo_entry.get("tier", "")
                rank_str = f"{tier_str} {solo_entry.get('rank', '')}"
                lp       = solo_entry.get("leaguePoints", 0)
                wins     = solo_entry.get("wins", 0)
                losses   = solo_entry.get("losses", 0)

            from datetime import datetime, timezone
            db.save_player({
                "puuid":      account["puuid"],
                "riot_id":    account.get("gameName", game_name.strip()),
                "tag":        account.get("tagLine", tag_line.strip()),
                "level":      summoner.get("summonerLevel", 0),
                "rank":       rank_str,
                "tier":       tier_str,
                "lp":         lp,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            db.save_config("puuid", account["puuid"])

        except RiotNotFoundError:
            st.error(
                f"No se encontró la cuenta **{game_name.strip()}#{tag_line.strip()}**. "
                "Verifica el nombre y tag."
            )
            return
        except RiotAPIError as e:
            st.error(f"Error de API: {e}")
            return

    st.rerun()
