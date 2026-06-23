"""
backend/draft/synergy_engine.py — Motor de sinergia candidato↔equipo.

Evalúa cuánto aporta un campeón candidato al equipo aliado en función
de los gaps detectados en el TeamProfile.

Principio: recompensar cuando el candidato cubre necesidades del equipo.
NO hay lógica por nombre de campeón. Todo sale de atributos.

Rango de salida: 0.0 – 20.0
"""

from __future__ import annotations

from .champion_profiles import ChampionProfile
from .draft_context import TeamProfile


# Umbral de cobertura esperada por miembro de equipo (valores calibrados)
_THRESHOLDS = {
    "engage":    2.0,
    "peel":      1.5,
    "cc":        2.0,
    "scaling":   2.5,
    "waveclear": 2.0,
    "anti_tank": 1.5,
}

# Peso máximo por dimensión (suma = 20)
_MAX = {
    "damage_diversity": 4.0,
    "engage_fill":      4.0,
    "peel_fill":        3.0,
    "scaling_fit":      5.0,   # la dimensión más importante para un carry
    "utility":          4.0,
}


def compute_synergy(
    candidate: ChampionProfile,
    team: TeamProfile,
) -> float:
    """
    Calcula el synergy score (0-20) del candidato con el equipo.

    Dimensiones
    -----------
    1. Diversidad de daño (0-4)
       El candidato aporta daño mágico/mixto si el equipo carece de él.

    2. Engage / CC gap (0-4)
       El candidato cubre la falta de engage o CC del equipo.

    3. Peel / Protección gap (0-3)
       El candidato aporta peel si el equipo no puede proteger carries.

    4. Fit de escalado (0-5)
       Maximiza el potencial del candidato según la estructura del equipo:
       - Si el equipo tiene engage fuerte → recompensar carries con alto scaling.
       - Si el equipo carece de engage → recompensar autos-suficiencia.

    5. Utilidad (anti-tank + waveclear gap) (0-4)
       El candidato cubre gaps de anti-tank o limpieza de oleadas.
    """
    if team.count == 0:
        # Sin datos de aliados: score neutro (mitad del máximo)
        return 10.0

    score = 0.0

    # ── 1. Diversidad de daño ─────────────────────────────────────────────────
    if team.needs_magic and candidate.damage_type in ("magic", "mixed"):
        # Equipo sin daño mágico + candidato lo aporta
        magic_contribution = (candidate.burst + candidate.sustained_damage) / 2
        score += min(_MAX["damage_diversity"], magic_contribution * 0.8)
    elif candidate.damage_type == "mixed":
        # Daño mixto siempre es difícil de defender; bonus menor
        score += 1.0

    # ── 2. Engage / CC gap ────────────────────────────────────────────────────
    engage_avg = team.avg("engage")
    cc_avg     = team.avg("cc")
    engage_gap = max(0.0, _THRESHOLDS["engage"] - engage_avg)
    cc_gap     = max(0.0, _THRESHOLDS["cc"]     - cc_avg)

    engage_fill = (
        engage_gap / _THRESHOLDS["engage"] *          # qué tan grande es el gap
        ((candidate.engage + candidate.cc) / 2) / 5 * # cuánto aporta el candidato
        _MAX["engage_fill"]
    )
    score += min(_MAX["engage_fill"], engage_fill)

    # ── 3. Peel gap ───────────────────────────────────────────────────────────
    peel_avg = team.avg("peel")
    if peel_avg < _THRESHOLDS["peel"]:
        peel_gap    = _THRESHOLDS["peel"] - peel_avg
        peel_factor = (candidate.peel + candidate.self_peel * 0.5) / 7.5
        score += min(_MAX["peel_fill"], peel_gap / _THRESHOLDS["peel"] * peel_factor * _MAX["peel_fill"])

    # ── 4. Fit de escalado ────────────────────────────────────────────────────
    if team.is_engage_heavy:
        # Equipo con mucho engage: maximizar carries con alto scaling
        scaling_fit = candidate.scaling / 5.0 * _MAX["scaling_fit"]
    elif team.lacks_engage:
        # Sin engage aliado: preferir auto-suficiencia + movilidad
        auto_suf = (candidate.mobility + candidate.self_peel) / 2
        scaling_fit = auto_suf / 5.0 * _MAX["scaling_fit"] * 0.8
    else:
        # Equipo balanceado: fit mixto
        scaling_fit = (candidate.scaling * 0.6 + candidate.sustained_damage * 0.4) / 5.0 * _MAX["scaling_fit"]

    score += min(_MAX["scaling_fit"], scaling_fit)

    # ── 5. Utilidad (anti-tank + waveclear) ───────────────────────────────────
    utility = 0.0
    if team.lacks_anti_tank and candidate.anti_tank >= 2:
        at_gap  = _THRESHOLDS["anti_tank"] - team.avg("anti_tank")
        utility += at_gap / _THRESHOLDS["anti_tank"] * candidate.anti_tank / 5.0 * 2.5

    if team.lacks_waveclear and candidate.waveclear >= 3:
        wc_gap  = _THRESHOLDS["waveclear"] - team.avg("waveclear")
        utility += wc_gap / _THRESHOLDS["waveclear"] * candidate.waveclear / 5.0 * 1.5

    score += min(_MAX["utility"], utility)

    return min(20.0, max(0.0, score))


def synergy_reasons(
    candidate: ChampionProfile,
    team: TeamProfile,
    synergy: float,
) -> list[str]:
    """
    Genera razones positivas derivadas del análisis de sinergia.
    Máximo 3 razones para no sobrecargar la UI.
    """
    if synergy < 4:
        return []

    reasons: list[str] = []

    # Daño
    if team.needs_magic and candidate.damage_type in ("magic", "mixed"):
        reasons.append("Aporta daño mágico que el equipo necesita")
    elif candidate.damage_type == "mixed":
        reasons.append("Daño mixto difícil de defender para el rival")

    # Engage / engage fill
    if team.lacks_engage and candidate.engage >= 2:
        reasons.append("Cubre la falta de engage del equipo")
    elif team.is_engage_heavy and candidate.scaling >= 4:
        reasons.append("Complementa el engage aliado con alto escalado")

    # Peel
    if team.lacks_peel and candidate.peel >= 2:
        reasons.append("Aporta peel para proteger carries aliados")

    # Escalado
    if team.is_engage_heavy and candidate.scaling >= 4 and not any("Complementa" in r for r in reasons):
        reasons.append("Escala bien respaldado por la composición aliada")

    # Anti-tank
    if team.lacks_anti_tank and candidate.anti_tank >= 3:
        reasons.append("Cubre el anti-tank que el equipo necesita")

    # Waveclear
    if team.lacks_waveclear and candidate.waveclear >= 4:
        reasons.append("Aporta limpieza de oleadas que faltaba al equipo")

    return reasons[:3]
