"""
backend/viewmodels/coaching_vm.py — ViewModel para la pantalla de Coaching.

Construye absolutamente todo lo que necesita ui/coaching.py para renderizar.
La UI no debe calcular nada: solo consumir este objeto y hacer st.* calls.

FastAPI (Sprint E-2):
    GET /coaching?role=ADC&limit=20
    return build_coaching(role, limit)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import db
import scorer_v2
import coaching_engine
from backend.services.champion_analyzer import analyze_champion_pool, ChampionPoolAnalysis
from backend.services.match_resolver import resolve_matches
from backend.services.priority_engine import compute_priorities, Priority
from backend.services.matchup_analyzer import analyze_matchups
from backend.services.matchup_models import MatchupResult
from backend.services.champion_coach import analyze_champion, get_available_champions
from backend.services.champion_models import ChampionCoachResult


# ── Helpers matemáticos puros ──────────────────────────────────────────────────

def _safe(match: dict, key: str) -> float | None:
    v = match.get(key)
    return float(v) if v is not None else None


def _avg(vals: list[float]) -> float | None:
    return sum(vals) / len(vals) if vals else None


# ── Estructura de datos ────────────────────────────────────────────────────────

@dataclass
class CoachingMetrics:
    """Promedios de métricas crudas extraídas de las partidas del rol."""
    cs_pm:       float | None
    dmg_pm:      float | None
    kp:          float | None
    kp_win:      float | None
    kp_loss:     float | None
    deaths:      float | None
    deaths_win:  float | None
    deaths_loss: float | None
    vision_pm:   float | None
    gold_pm:     float | None
    obj_pm:      float | None
    n:           int
    n_wins:      int
    n_losses:    int


@dataclass
class CoachingViewModel:
    # Estado del jugador
    player_name:     str
    rank:            str
    lp:              int
    last_match_date: str | None

    # Análisis principal
    score_result:    scorer_v2.ScoreResultV2
    coaching_result: coaching_engine.CoachingResult
    metrics:         CoachingMetrics
    priorities:      list[Priority]
    matchup_result:  MatchupResult | None
    champion_pool:   ChampionPoolAnalysis | None

    # Datos para Champion Coach
    available_champions: list[str]

    # Metadatos
    role:        str
    sample_size: int
    has_data:    bool

    # Matches crudas (necesarias para renders de gráficos y resumen)
    role_matches: list[dict] = field(default_factory=list)


# ── Constructor ────────────────────────────────────────────────────────────────

def build_coaching(role: str, limit: int = 20) -> CoachingViewModel:
    """
    Construye el ViewModel completo para la pantalla de Coaching.

    Parámetros
    ----------
    role  : "ADC" | "TOP"
    limit : número de partidas a analizar

    Retorna
    -------
    CoachingViewModel con todos los datos precalculados.
    """
    puuid  = db.get_config("puuid")
    player = db.get_player(puuid) if puuid else None

    player_name     = player["riot_id"] if player else "Invocador"
    rank            = player.get("rank", "Sin rango") if player else "—"
    lp              = player.get("lp", 0) if player else 0

    # Partidas del rol en la ventana solicitada
    all_matches  = resolve_matches(limit=max(limit + 50, 200))
    role_matches = [m for m in all_matches if m.get("role") == role][:limit]

    # Fecha del último dato disponible
    recent = resolve_matches(limit=1)
    last_match_date = recent[0]["played_at"][:10] if recent and recent[0].get("played_at") else None

    if not role_matches:
        # Sin datos — ViewModel vacío válido
        return CoachingViewModel(
            player_name=player_name,
            rank=rank,
            lp=lp,
            last_match_date=last_match_date,
            score_result=None,       # type: ignore[arg-type]
            coaching_result=None,    # type: ignore[arg-type]
            metrics=CoachingMetrics(
                cs_pm=None, dmg_pm=None, kp=None, kp_win=None, kp_loss=None,
                deaths=None, deaths_win=None, deaths_loss=None,
                vision_pm=None, gold_pm=None, obj_pm=None,
                n=0, n_wins=0, n_losses=0,
            ),
            priorities=[],
            matchup_result=None,
            champion_pool=None,
            available_champions=[],
            role=role,
            sample_size=0,
            has_data=False,
            role_matches=[],
        )

    # ── Motores de análisis ────────────────────────────────────────────────────
    score_result    = scorer_v2.analyze_player(role_matches, role)
    coaching_result = coaching_engine.analyze_coaching(score_result, role_matches, role)
    priorities      = compute_priorities(role_matches, role)
    matchup_result  = analyze_matchups(role_matches, role)
    champion_pool   = analyze_champion_pool(role_matches, role, score_result.match_scores)

    # ── Métricas crudas ────────────────────────────────────────────────────────
    metrics = _compute_metrics(role_matches)

    return CoachingViewModel(
        player_name=player_name,
        rank=rank,
        lp=lp,
        last_match_date=last_match_date,
        score_result=score_result,
        coaching_result=coaching_result,
        metrics=metrics,
        priorities=priorities,
        matchup_result=matchup_result,
        champion_pool=champion_pool,
        available_champions=get_available_champions(role_matches),
        role=role,
        sample_size=len(role_matches),
        has_data=True,
        role_matches=role_matches,
    )


def build_champion_coach(
    vm: CoachingViewModel,
    champion: str,
) -> ChampionCoachResult:
    """
    Construye el análisis de Champion Coach para un campeón específico.
    Se llama después de build_coaching() cuando el usuario selecciona un campeón.
    """
    return analyze_champion(
        matches=vm.role_matches,
        champion=champion,
        role=vm.role,
        all_role_matches=vm.role_matches,
        matchup_result=vm.matchup_result,
    )


# ── Privado ────────────────────────────────────────────────────────────────────

def _compute_metrics(matches: list[dict]) -> CoachingMetrics:
    """Calcula promedios de métricas relevantes desde datos crudos."""
    if not matches:
        return CoachingMetrics(
            cs_pm=None, dmg_pm=None, kp=None, kp_win=None, kp_loss=None,
            deaths=None, deaths_win=None, deaths_loss=None,
            vision_pm=None, gold_pm=None, obj_pm=None,
            n=0, n_wins=0, n_losses=0,
        )

    wins   = [m for m in matches if m.get("result") == "WIN"]
    losses = [m for m in matches if m.get("result") == "LOSS"]

    def avg_field(lst: list[dict], key: str) -> float | None:
        vals = [_safe(m, key) for m in lst]
        vals = [v for v in vals if v is not None]
        return _avg(vals)

    def avg_pm(lst: list[dict], key: str) -> float | None:
        vals = [_safe(m, key) for m in lst]
        durs = [max(m.get("duration_sec", 60) / 60, 1.0) for m in lst]
        pairs = [(v, d) for v, d in zip(vals, durs) if v is not None]
        return _avg([v / d for v, d in pairs]) if pairs else None

    kp_vals = [_safe(m, "kill_participation") for m in matches]
    kp_vals = [v for v in kp_vals if v is not None]
    kp_win  = [_safe(m, "kill_participation") for m in wins  if _safe(m, "kill_participation") is not None]
    kp_loss = [_safe(m, "kill_participation") for m in losses if _safe(m, "kill_participation") is not None]

    return CoachingMetrics(
        cs_pm=       avg_pm(matches, "cs"),
        dmg_pm=      avg_pm(matches, "damage"),
        kp=          _avg(kp_vals) if kp_vals else None,
        kp_win=      _avg(kp_win)  if kp_win  else None,
        kp_loss=     _avg(kp_loss) if kp_loss else None,
        deaths=      avg_field(matches, "deaths"),
        deaths_win=  avg_field(wins,    "deaths"),
        deaths_loss= avg_field(losses,  "deaths"),
        vision_pm=   avg_pm(matches, "vision_score"),
        gold_pm=     avg_pm(matches, "gold_earned"),
        obj_pm=      avg_pm(matches, "objective_damage"),
        n=           len(matches),
        n_wins=      len(wins),
        n_losses=    len(losses),
    )
