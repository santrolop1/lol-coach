"""
ui/config.py — Página de configuración.

Permite al usuario:
- Ingresar y guardar su API Key de Riot.
- Ingresar su Riot ID (nombre#tag).
- Seleccionar su región/plataforma.
- Verificar que la conexión funciona.
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


def render() -> None:
    st.title("⚙️ Configuración")
    st.markdown("Configura tu cuenta para empezar a analizar tus partidas.")

    # ----------------------------------------------------------------
    # Cargar valores guardados
    # ----------------------------------------------------------------
    saved_key      = db.get_config("api_key")      or ""
    saved_name     = db.get_config("game_name")    or ""
    saved_tag      = db.get_config("tag_line")     or ""
    saved_platform = db.get_config("platform")     or "la1"

    # Encontrar el label del platform guardado
    platform_labels = list(PLATFORMS.keys())
    platform_values = list(PLATFORMS.values())
    default_idx = platform_values.index(saved_platform) if saved_platform in platform_values else 0

    # ----------------------------------------------------------------
    # Formulario
    # ----------------------------------------------------------------
    with st.form("config_form"):
        st.subheader("🔑 Riot Developer API Key")
        st.markdown(
            "Obtén tu clave en [developer.riotgames.com](https://developer.riotgames.com). "
            "La Dev Key expira cada 24h — recuérdala regenerar."
        )
        api_key = st.text_input(
            "API Key",
            value=saved_key,
            type="password",
            placeholder="RGAPI-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        )

        st.divider()
        st.subheader("👤 Tu Riot ID")
        col1, col2 = st.columns([3, 1])
        with col1:
            game_name = st.text_input("Nombre de invocador", value=saved_name, placeholder="NombreEjemplo")
        with col2:
            tag_line = st.text_input("Tag", value=saved_tag, placeholder="LA1")

        st.subheader("🌍 Región")
        platform_label = st.selectbox(
            "Servidor donde juegas",
            options=platform_labels,
            index=default_idx,
        )

        submitted = st.form_submit_button("💾 Guardar configuración", use_container_width=True)

    # ----------------------------------------------------------------
    # Guardar
    # ----------------------------------------------------------------
    if submitted:
        if not api_key.strip():
            st.error("La API Key no puede estar vacía.")
            return
        if not game_name.strip():
            st.error("El nombre de invocador no puede estar vacío.")
            return
        if not tag_line.strip():
            st.error("El tag no puede estar vacío.")
            return

        platform = PLATFORMS[platform_label]

        db.save_config("api_key",   api_key.strip())
        db.save_config("game_name", game_name.strip())
        db.save_config("tag_line",  tag_line.strip().lstrip("#"))
        db.save_config("platform",  platform)

        st.success("✅ Configuración guardada.")

    # ----------------------------------------------------------------
    # Verificar conexión
    # ----------------------------------------------------------------
    st.divider()
    st.subheader("🔗 Verificar conexión")

    if st.button("Probar API Key y buscar cuenta", use_container_width=True):
        current_key      = db.get_config("api_key")
        current_name     = db.get_config("game_name")
        current_tag      = db.get_config("tag_line")
        current_platform = db.get_config("platform") or "la1"

        if not current_key or not current_name or not current_tag:
            st.warning("Guarda la configuración antes de verificar.")
            return

        with st.spinner("Conectando con Riot API..."):
            try:
                client = RiotClient(current_key, current_platform)
                account = client.get_account(current_name, current_tag)
                summoner = client.get_summoner(account["puuid"])
                league_entries = client.get_league_by_puuid(account["puuid"])

                # Rank
                solo_entry = next(
                    (e for e in league_entries if e.get("queueType") == "RANKED_SOLO_5x5"),
                    None,
                )

                rank_str = "Sin rango"
                lp, wins, losses = 0, 0, 0
                tier_str = ""
                if solo_entry:
                    tier_str = solo_entry.get("tier", "")
                    rank_str = f"{tier_str} {solo_entry.get('rank', '')}"
                    lp       = solo_entry.get("leaguePoints", 0)
                    wins     = solo_entry.get("wins", 0)
                    losses   = solo_entry.get("losses", 0)

                # Guardar en DB
                from datetime import datetime, timezone
                db.save_player({
                    "puuid":      account["puuid"],
                    "riot_id":    account.get("gameName", current_name),
                    "tag":        account.get("tagLine", current_tag),
                    "level":      summoner.get("summonerLevel", 0),
                    "rank":       rank_str,
                    "tier":       tier_str,
                    "lp":         lp,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                })
                db.save_config("puuid", account["puuid"])

                # Mostrar resultado
                st.success(f"✅ Cuenta encontrada: **{account.get('gameName', current_name)}#{account.get('tagLine', current_tag)}**")
                col1, col2, col3 = st.columns(3)
                col1.metric("Nivel", summoner.get("summonerLevel", "—"))
                col2.metric("Rango", rank_str if rank_str != "Sin rango" else "Sin rango")
                col3.metric("LP", lp)
                if wins or losses:
                    total = wins + losses
                    wr = round(wins / total * 100, 1) if total else 0
                    st.caption(f"Ranked Solo: {wins}W / {losses}L — {wr}% WR")

            except RiotNotFoundError:
                st.error(f"❌ No se encontró la cuenta **{current_name}#{current_tag}**. Verifica el nombre y tag.")
            except RiotAPIError as e:
                st.error(f"❌ Error de API: {e}")
