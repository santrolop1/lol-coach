"""
backend/draft/threat_engine.py — Motor de amenaza candidato↔enemigos.

Evalúa cuánto penaliza la composición enemiga al candidato.

Principio: penalizar cuando el candidato tiene atributos de defensa bajos
frente a amenazas enemigas detectadas en el EnemyProfile.

NO hay lógica por nombre de campeón. Todo sale de atributos.

Rango de salida: -20.0 – 0.0
  0 = sin penalización (candidato se defiende bien)
-20 = muy vulnerable a la composición enemiga
"""

from __future__ import annotations

from .champion_profiles import ChampionProfile
from .draft_context import EnemyProfile


def compute_threat(
    candidate: ChampionProfile,
    enemy: EnemyProfile,
) -> float:
    """
    Calcula el threat score (-20 a 0) del candidato frente al equipo enemigo.

    Dimensiones de penalización
    ---------------------------
    1. Amenaza de dive  (-0 a -5)
       Si enemigos pueden alcanzar carries y el candidato no puede escapar.

    2. Amenaza de burst (-0 a -5)
       Si enemigos tienen alto burst y el candidato no tiene defensas.

    3. Amenaza de CC    (-0 a -5)
       Si enemigos tienen CC pesado y el candidato no tiene movilidad.

    4. Anti-tank        (-0 a -3)
       Si enemigos tienen anti-tank y el candidato es tanque.

    5. Escalado tardío  (-0 a -2)
       Si enemigos escalan muy fuerte y el candidato tiene bajo daño.
    """
    if enemy.count == 0:
        return 0.0  # Sin información enemiga: sin penalización

    penalty = 0.0

    # ── 1. Dive threat ────────────────────────────────────────────────────────
    if enemy.high_dive:
        # Cuánto puede el candidato escapar / resistir el dive
        escape = (candidate.mobility + candidate.self_peel) / 2  # 0-5
        vulnerability = max(0.0, 5.0 - escape) / 5.0             # 1.0 = sin defensa
        penalty -= vulnerability * 5.0

    # ── 2. Burst threat ───────────────────────────────────────────────────────
    if enemy.high_burst:
        # Defensa contra burst: movilidad para evitar + algo de aguante
        defense = (candidate.mobility * 0.6 + candidate.tankiness * 0.4)  # 0-5
        vulnerability = max(0.0, 4.5 - defense) / 4.5
        penalty -= vulnerability * 5.0

    # ── 3. CC threat ──────────────────────────────────────────────────────────
    if enemy.heavy_cc:
        # La movilidad es la principal defensa contra el CC (dashes ante habilidades)
        escape = candidate.mobility  # 0-5
        vulnerability = max(0.0, 4.0 - escape) / 4.0
        penalty -= vulnerability * 5.0

    # ── 4. Anti-tank ─────────────────────────────────────────────────────────
    if enemy.has_anti_tank and candidate.tankiness >= 3:
        # Penaliza al candidato tanque cuando el enemigo lo contrarresta
        at_severity = min(1.0, enemy.avg_anti_tank / 4.0)
        penalty -= at_severity * 3.0

    # ── 5. Late-scaling enemigo + bajo daño propio ────────────────────────────
    if enemy.late_scaling:
        # Si el candidato no puede acabar la partida antes de que el enemigo escale
        candidate_dmg = (candidate.burst + candidate.sustained_damage) / 2
        if candidate_dmg < 2.0:
            penalty -= 2.0

    return max(-20.0, penalty)


def threat_reasons(
    candidate: ChampionProfile,
    enemy: EnemyProfile,
    threat: float,
) -> list[str]:
    """
    Genera razones negativas derivadas del análisis de amenaza.
    Máximo 2 razones para no sobrecargar la UI.
    """
    if threat > -3:
        return []

    reasons: list[str] = []

    if enemy.high_dive:
        escape = (candidate.mobility + candidate.self_peel) / 2
        if escape < 2.5:
            reasons.append("Vulnerable frente a la composición de dive enemiga")

    if enemy.high_burst:
        defense = (candidate.mobility * 0.6 + candidate.tankiness * 0.4)
        if defense < 2.5:
            reasons.append("Vulnerable al alto burst del equipo enemigo")

    if enemy.heavy_cc:
        if candidate.mobility < 2:
            reasons.append("Poco escape frente al CC pesado del enemigo")

    if enemy.has_anti_tank and candidate.tankiness >= 3:
        reasons.append("El anti-tank enemigo reduce tu efectividad ofensiva")

    if enemy.late_scaling and (candidate.burst + candidate.sustained_damage) / 2 < 2:
        reasons.append("Riesgo alto si la partida llega al late game enemigo")

    return reasons[:2]
