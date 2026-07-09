"""
backend/viewmodels/matches_vm.py — ViewModel para la pantalla de Partidas.

Construye todo lo que necesita ui/matches.py para renderizar.
La UI no calcula scores, no aplica filtros, no formatea filas.

FastAPI (Sprint E-2):
    GET /matches?role=ADC&champion=Jinx
    return build_matches(role_filter, champion_filter)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import db
import scorer_v2
from scorer import calculate_score


# ── Estructuras de datos ───────────────────────────────────────────────────────

@dataclass
class MatchCard:
    """Datos para renderizar una tarjeta compacta de partida."""
    is_win:        bool
    champion:      str
    role:          str
    kda:           str
    overall_score: float
    best_dim:      str
    worst_dim:     str
    match_id:      str


@dataclass
class MatchRow:
    """Fila de la tabla de historial completo."""
    result:   str
    champion: str
    role:     str
    kda:      str
    cs:       int
    cs_pm:    float
    damage:   str
    duration: str
    date:     str


@dataclass
class MatchDetailRow:
    """Fila del análisis V2 detallado (dentro del expander)."""
    date:       str
    champion:   str
    result:     str
    overall:    float
    kda:        str
    dimensions: dict[str, float]


@dataclass
class MatchesSummary:
    """Resumen estadístico del historial filtrado."""
    total:   int
    wins:    int
    losses:  int
    winrate: float


@dataclass
class MatchesV2Analysis:
    """Análisis V2 para un rol concreto (solo cuando hay rol filtrado)."""
    role:         str
    detail_rows:  list[MatchDetailRow]
    avg_overall:  float
    avg_dims:     dict[str, float]
    available:    bool  # False si hay menos de 5 partidas


@dataclass
class MatchesViewModel:
    has_config:      bool
    player:          dict | None
    recent_cards:    list[MatchCard]      # últimas 5 partidas ADC/TOP
    table_rows:      list[MatchRow]       # historial completo filtrado
    summary:         MatchesSummary
    v2_analysis:     MatchesV2Analysis | None
    available_roles: list[str]            # roles distintos en la DB
    available_champs: list[str]           # campeones para el filtro


# ── Constructor ────────────────────────────────────────────────────────────────

def build_matches(
    role_filter:    str | None = None,
    champion_filter: str | None = None,
) -> MatchesViewModel:
    """
    Construye el ViewModel completo para la pantalla de Partidas.

    Parámetros
    ----------
    role_filter     : "ADC" | "TOP" | None (sin filtro)
    champion_filter : nombre exacto del campeón o None

    Retorna
    -------
    MatchesViewModel con todos los datos precalculados.
    """
    puuid    = db.get_config("puuid")
    platform = db.get_config("platform") or "la1"

    if not puuid:
        return MatchesViewModel(
            has_config=False,
            player=None,
            recent_cards=[],
            table_rows=[],
            summary=MatchesSummary(total=0, wins=0, losses=0, winrate=0.0),
            v2_analysis=None,
            available_roles=[],
            available_champs=[],
        )

    player = db.get_player(puuid)

    # ── Tarjetas de las 5 partidas más recientes ───────────────────────────────
    all_recent = db.get_matches(puuid, limit=100)
    adc_top    = [m for m in all_recent if m["role"] in ("ADC", "TOP")]
    recent_cards = [_build_card(m) for m in adc_top[:20]]

    # ── Historial filtrado ─────────────────────────────────────────────────────
    role_arg    = None if role_filter in (None, "Todos") else role_filter
    all_matches = db.get_matches(puuid, role=role_arg, limit=100)

    champions = sorted({m["champion"] for m in all_matches if m["champion"]})

    filtered = all_matches
    if champion_filter and champion_filter != "Todos":
        filtered = [m for m in filtered if m["champion"] == champion_filter]

    table_rows = [_build_row(m) for m in filtered]

    wins    = sum(1 for m in filtered if m["result"] == "WIN")
    losses  = len(filtered) - wins
    winrate = round(wins / len(filtered) * 100, 1) if filtered else 0.0

    summary = MatchesSummary(
        total=len(filtered),
        wins=wins,
        losses=losses,
        winrate=winrate,
    )

    # ── Análisis V2 (solo con rol concreto) ───────────────────────────────────
    v2_analysis = None
    if role_filter and role_filter not in (None, "Todos"):
        role_matches = [m for m in filtered if m["role"] == role_filter]
        if len(role_matches) >= 5:
            sr       = scorer_v2.analyze_player(role_matches, role_filter)
            dim_names = [d.name for d in sr.match_scores[0].dimensions] if sr.match_scores else []

            detail_rows = []
            for m, ms in zip(role_matches, sr.match_scores):
                detail_rows.append(MatchDetailRow(
                    date=      (m.get("played_at") or "")[:10],
                    champion=  m.get("champion", "?"),
                    result=    "✅" if m.get("result") == "WIN" else "❌",
                    overall=   round(ms.overall_score, 1) if ms.overall_score else 0,
                    kda=       f"{m.get('kills',0)}/{m.get('deaths',0)}/{m.get('assists',0)}",
                    dimensions={d.name: round(d.score, 1) for d in ms.dimensions},
                ))

            v2_analysis = MatchesV2Analysis(
                role=        role_filter,
                detail_rows= detail_rows,
                avg_overall= sr.overall_score,
                avg_dims=    sr.dimensions,
                available=   True,
            )
        else:
            v2_analysis = MatchesV2Analysis(
                role=role_filter, detail_rows=[], avg_overall=0.0,
                avg_dims={}, available=False,
            )

    return MatchesViewModel(
        has_config=True,
        player=player,
        recent_cards=recent_cards,
        table_rows=table_rows,
        summary=summary,
        v2_analysis=v2_analysis,
        available_roles=["ADC", "TOP"],
        available_champs=champions,
    )


# ── Privado ────────────────────────────────────────────────────────────────────

def _build_card(m: dict) -> MatchCard:
    sc   = calculate_score(m)
    dims = {"Farm": sc.farm_score, "Superv": sc.survival_score, "Pelea": sc.fight_score}
    return MatchCard(
        is_win=        m["result"] == "WIN",
        champion=      m.get("champion", "?"),
        role=          m.get("role", "?"),
        kda=           f"{m.get('kills',0)}/{m.get('deaths',0)}/{m.get('assists',0)}",
        overall_score= sc.overall_score,
        best_dim=      max(dims, key=dims.get),
        worst_dim=     min(dims, key=dims.get),
        match_id=      m.get("match_id", ""),
    )


def _build_row(m: dict) -> MatchRow:
    dur_sec = m.get("duration_sec") or 1
    dur_min = dur_sec // 60
    dur_s   = dur_sec % 60
    cs_pm   = round((m.get("cs") or 0) / max(dur_sec / 60, 1), 1)
    return MatchRow(
        result=   "✅ Victoria" if m["result"] == "WIN" else "❌ Derrota",
        champion= m.get("champion") or "—",
        role=     m.get("role") or "—",
        kda=      f"{m.get('kills') or 0}/{m.get('deaths') or 0}/{m.get('assists') or 0}",
        cs=       m.get("cs") or 0,
        cs_pm=    cs_pm,
        damage=   f"{m.get('damage') or 0:,}",
        duration= f"{dur_min}m {dur_s:02d}s",
        date=     (m.get("played_at") or "")[:10],
    )
