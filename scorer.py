"""
scorer.py — Motor de scoring: convierte métricas de partida en scores 0-100.

Scores calculados:
  FarmScore     → qué tan bien farmeas (CS/min)
  SurvivalScore → qué tan bien sobrevives (muertes + KDA)
  FightScore    → qué tan bien peleas (daño/min + KDA)
  OverallScore  → promedio ponderado de los tres

Benchmarks calibrados para Gold/Plat (ajústalos con tus propias partidas).
"""

from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Resultado del scoring
# ---------------------------------------------------------------------------

@dataclass
class ScoreResult:
    farm_score:     float  # 0-100
    survival_score: float  # 0-100
    fight_score:    float  # 0-100
    overall_score:  float  # 0-100 (ponderado)

    def to_dict(self) -> dict:
        return {
            "farm_score":     self.farm_score,
            "survival_score": self.survival_score,
            "fight_score":    self.fight_score,
            "overall_score":  self.overall_score,
        }


# ---------------------------------------------------------------------------
# Benchmarks por rol
# Escala: bad=0 puntos, good=100 puntos (interpolación lineal entre ellos)
# ---------------------------------------------------------------------------

BENCHMARKS: dict[str, dict] = {
    "ADC": {
        # CS/min: ADC debe priorizar farmeo sobre todo
        "cs_per_min_bad":  4.5,
        "cs_per_min_good": 7.5,
        # Daño/min: ADC es el principal dealer de daño
        "dmg_per_min_bad":  350.0,
        "dmg_per_min_good": 900.0,
        # KDA: (kills + assists) / deaths
        "kda_bad":  1.0,
        "kda_good": 4.0,
        # Muertes por partida: menos es mejor (inverted benchmark)
        "deaths_bad":  7.0,   # 7 muertes → score 0
        "deaths_good": 1.0,   # 1 muerte   → score 100
    },
    "TOP": {
        "cs_per_min_bad":  4.0,
        "cs_per_min_good": 7.0,
        "dmg_per_min_bad":  250.0,
        "dmg_per_min_good": 700.0,
        "kda_bad":  1.0,
        "kda_good": 3.5,
        "deaths_bad":  7.0,
        "deaths_good": 1.0,
    },
}

# Fallback si el rol no está en benchmarks (partidas de OTRO rol)
_DEFAULT = BENCHMARKS["ADC"]


# ---------------------------------------------------------------------------
# Normalización
# ---------------------------------------------------------------------------

def _normalize(value: float, bad: float, good: float) -> float:
    """
    Mapea `value` al rango [0, 100].
    - Si value == bad  → 0
    - Si value == good → 100
    - Funciona tanto con bad < good (más es mejor) como bad > good (menos es mejor).
    """
    if good == bad:
        return 50.0
    raw = (value - bad) / (good - bad) * 100.0
    return max(0.0, min(100.0, raw))


# ---------------------------------------------------------------------------
# Función principal
# ---------------------------------------------------------------------------

def calculate_score(match: dict) -> ScoreResult:
    """
    Recibe un dict de la tabla `match` (o MatchData.to_dict()) y devuelve ScoreResult.

    Campos requeridos: role, kills, deaths, assists, cs, damage, duration_sec
    """
    role  = match.get("role", "ADC")
    bench = BENCHMARKS.get(role, _DEFAULT)

    # Duración en minutos (mínimo 1 para evitar división por cero)
    duration_min = max(match.get("duration_sec", 60) / 60.0, 1.0)

    kills   = match.get("kills",   0)
    deaths  = match.get("deaths",  0)
    assists = match.get("assists", 0)
    cs      = match.get("cs",      0)
    damage  = match.get("damage",  0)

    cs_per_min  = cs     / duration_min
    dmg_per_min = damage / duration_min
    kda         = (kills + assists) / max(deaths, 1)

    # --- FarmScore (100% peso en CS/min) ---
    farm_score = _normalize(
        cs_per_min,
        bench["cs_per_min_bad"],
        bench["cs_per_min_good"],
    )

    # --- SurvivalScore (50% muertes + 50% KDA) ---
    deaths_score = _normalize(deaths, bench["deaths_bad"], bench["deaths_good"])
    kda_score    = _normalize(kda,    bench["kda_bad"],    bench["kda_good"])
    survival_score = deaths_score * 0.5 + kda_score * 0.5

    # --- FightScore (60% daño/min + 40% KDA) ---
    dmg_score  = _normalize(dmg_per_min, bench["dmg_per_min_bad"], bench["dmg_per_min_good"])
    fight_score = dmg_score * 0.6 + kda_score * 0.4

    # --- OverallScore (ponderado) ---
    # Farm pesa 35%: el farmeo es la base del ADC y TOP
    # Survival pesa 30%: morir resetea todo el trabajo
    # Fight pesa 35%: el impacto en pelea cierra partidas
    overall_score = farm_score * 0.35 + survival_score * 0.30 + fight_score * 0.35

    return ScoreResult(
        farm_score=     round(farm_score,     1),
        survival_score= round(survival_score, 1),
        fight_score=    round(fight_score,    1),
        overall_score=  round(overall_score,  1),
    )


# ---------------------------------------------------------------------------
# Utilidad: score promedio de una lista de partidas
# ---------------------------------------------------------------------------

def average_scores(matches: list[dict]) -> ScoreResult | None:
    """Calcula el ScoreResult promedio de una lista de partidas."""
    if not matches:
        return None
    scores = [calculate_score(m) for m in matches]
    n = len(scores)
    return ScoreResult(
        farm_score=     round(sum(s.farm_score     for s in scores) / n, 1),
        survival_score= round(sum(s.survival_score for s in scores) / n, 1),
        fight_score=    round(sum(s.fight_score    for s in scores) / n, 1),
        overall_score=  round(sum(s.overall_score  for s in scores) / n, 1),
    )
