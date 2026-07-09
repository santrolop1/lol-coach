"""
backend/viewmodels/draft_vm.py — ViewModel para la pantalla de Draft.

Construye el estado actual del draft (LCU + análisis) sin depender de Streamlit.
Dado que el draft cambia cada 750ms, el ViewModel se construye en cada ciclo
y la UI decide si cachear (via session_state) o no.

FastAPI (Sprint E-2):
    GET /draft
    return build_draft()
    (o WebSocket para push en tiempo real)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import db
import scorer_v2
import lcu.client as lcu_client
from backend.services.match_resolver import resolve_matches
from backend.services.champion_analyzer import analyze_champion_pool, ChampionPoolAnalysis
from backend.services.draft_advisor import analyze_draft, DraftAdvice
from lcu.champ_select import parse_session, PHASE_LABELS, GAMEFLOW_LABELS
from lcu.models import ChampSelectSession, LCUCredentials


# Roles con soporte en scorer_v2
_SUPPORTED_ROLES: frozenset[str] = frozenset({"ADC", "TOP"})

_LCU_TO_ROLE: dict[str, str] = {
    "bottom":  "ADC",
    "top":     "TOP",
    "middle":  "MID",
    "jungle":  "JGL",
    "utility": "SUP",
}


# ── Estructuras de datos ───────────────────────────────────────────────────────

@dataclass
class DraftViewModel:
    """Estado completo del draft en un instante dado."""
    # Conexión LCU
    lcu_connected:  bool
    credentials:    LCUCredentials | None

    # Fase del juego
    phase:          str | None          # "ChampSelect", "InProgress", "Lobby", etc.
    phase_label:    str                 # texto legible para la UI

    # Solo presente durante ChampSelect
    session:        ChampSelectSession | None
    champion_map:   dict[int, str]      # {champion_id: champion_name}
    advice:         DraftAdvice | None
    champion_pool:  ChampionPoolAnalysis | None

    # Rol detectado del jugador
    role:           str | None          # "ADC" | "TOP" | None
    role_supported: bool                # True si hay análisis disponible para el rol


# ── Constructor ────────────────────────────────────────────────────────────────

def build_draft(
    lcu_puuid: str | None = None,
    champion_map_cache: dict[int, str] | None = None,
    cpa_cache: dict[str, ChampionPoolAnalysis] | None = None,
) -> DraftViewModel:
    """
    Construye el ViewModel del draft leyendo el estado actual del LCU.

    Parámetros
    ----------
    lcu_puuid          : PUUID reportado por el LCU (para resolve_matches).
    champion_map_cache : cache externo del mapa {id: nombre} (opcional, evita
                         re-fetching en cada ciclo). La UI gestiona este cache.
    cpa_cache          : cache externo de ChampionPoolAnalysis por rol. La UI
                         gestiona este cache para evitar recalcular en cada frame.

    Retorna
    -------
    DraftViewModel con el estado actual completo.
    """
    # ── Credenciales LCU ──────────────────────────────────────────────────────
    creds = lcu_client.read_credentials()

    if creds is None:
        return DraftViewModel(
            lcu_connected=False,
            credentials=None,
            phase=None,
            phase_label="Desconectado",
            session=None,
            champion_map={},
            advice=None,
            champion_pool=None,
            role=None,
            role_supported=False,
        )

    # ── Fase actual ───────────────────────────────────────────────────────────
    phase = lcu_client.get_phase(creds)
    phase_label = GAMEFLOW_LABELS.get(phase, phase or "Desconocido")

    if phase != "ChampSelect":
        return DraftViewModel(
            lcu_connected=True,
            credentials=creds,
            phase=phase,
            phase_label=phase_label,
            session=None,
            champion_map={},
            advice=None,
            champion_pool=None,
            role=None,
            role_supported=False,
        )

    # ── ChampSelect activo ────────────────────────────────────────────────────
    raw_session = lcu_client.get_champ_select_session(creds)
    if raw_session is None:
        return DraftViewModel(
            lcu_connected=True,
            credentials=creds,
            phase="ChampSelect",
            phase_label="Cargando sesión…",
            session=None,
            champion_map={},
            advice=None,
            champion_pool=None,
            role=None,
            role_supported=False,
        )

    # Mapa de campeones (usa cache externo solo si tiene contenido; si está vacío, re-fetcha)
    champ_map = champion_map_cache if champion_map_cache else lcu_client.get_champion_map(creds)

    session = parse_session(raw_session, champ_map)

    # Rol del jugador
    lcu_role       = session.my_role or ""
    role           = _LCU_TO_ROLE.get(lcu_role, "")
    role_supported = role in _SUPPORTED_ROLES

    # Champion Pool Analysis (usa cache externo si disponible)
    champion_pool: ChampionPoolAnalysis | None = None
    advice:        DraftAdvice | None = None

    if role_supported:
        cache_key = role
        if cpa_cache is not None and cache_key in cpa_cache:
            champion_pool = cpa_cache[cache_key]
        else:
            matches = resolve_matches(role=role, extra_puuid=lcu_puuid)
            if matches:
                sr            = scorer_v2.analyze_player(matches, role)
                champion_pool = analyze_champion_pool(matches, role, sr.match_scores)
                if cpa_cache is not None:
                    cpa_cache[cache_key] = champion_pool

        if champion_pool is not None:
            advice = analyze_draft(session, champion_pool)

    return DraftViewModel(
        lcu_connected=True,
        credentials=creds,
        phase="ChampSelect",
        phase_label="Champ Select",
        session=session,
        champion_map=champ_map,
        advice=advice,
        champion_pool=champion_pool,
        role=role or None,
        role_supported=role_supported,
    )
