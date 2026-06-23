"""
backend/draft/draft_advisor_v2.py — Enriquecimiento contextual de recomendaciones.

Toma el DraftAdvice existente (basado en historial) y añade análisis contextual
del draft actual (sinergia con aliados, amenaza de enemigos).

El resultado es un DraftContextResult con:
  - pick_value     : score histórico (heredado del DraftAdvice v1)
  - synergy        : puntuación de sinergia (0-20)
  - threat         : penalización de amenaza (-20 a 0)
  - draft_score_v2 : composite score contextual (0-100)
  - reasons        : razones positivas + negativas

Solo depende de atributos de perfil. NO hay lógica por nombre de campeón.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .champion_profiles import get_profile
from .draft_context import TeamProfile, EnemyProfile
from .profile_builder import build_team_profile, build_enemy_profile
from .synergy_engine import compute_synergy, synergy_reasons
from .threat_engine import compute_threat, threat_reasons
from .draft_score_v2 import compute_draft_score_v2


@dataclass
class DraftContextScore:
    """
    Puntuación contextual completa de un campeón candidato.
    """
    champion:        str
    pick_value:      float          # score histórico 0-100
    synergy:         float          # 0-20
    threat:          float          # -20 a 0
    draft_score_v2:  float          # composite 0-100
    pos_reasons:     list[str] = field(default_factory=list)  # sinergia
    neg_reasons:     list[str] = field(default_factory=list)  # amenaza
    context_available: bool = True  # False si no hay datos aliados/enemigos


@dataclass
class DraftContextResult:
    """
    Resultado de la contextualización de todas las recomendaciones.
    """
    scores:         dict[str, DraftContextScore]  # {champion_lower: score}
    team_profile:   TeamProfile
    enemy_profile:  EnemyProfile
    ally_coverage:  int    # campeones aliados con perfil encontrado
    enemy_coverage: int    # campeones enemigos con perfil encontrado


def enhance_recommendations(
    recommendations: list,           # list[DraftRecommendation] de draft_advisor.py
    ally_names:   list[str],         # nombres de campeones aliados ya pickeados
    enemy_names:  list[str],         # nombres de campeones enemigos ya pickeados
) -> DraftContextResult:
    """
    Añade contexto de draft a una lista de recomendaciones existentes.

    Parámetros
    ----------
    recommendations : lista de DraftRecommendation del advisor v1
    ally_names      : campeones aliados (sin contar al propio jugador)
    enemy_names     : campeones enemigos

    Retorna
    -------
    DraftContextResult con el score contextual de cada campeón.
    """
    team_profile  = build_team_profile(ally_names)
    enemy_profile = build_enemy_profile(enemy_names)

    scores: dict[str, DraftContextScore] = {}

    for rec in recommendations:
        champ_name = rec.champion
        profile    = get_profile(champ_name)

        if profile is None:
            # Campeón no catalogado: solo score histórico sin contexto
            ctx = DraftContextScore(
                champion         = champ_name,
                pick_value       = rec.avg_score,
                synergy          = 10.0,  # neutro
                threat           = 0.0,   # sin penalización
                draft_score_v2   = rec.avg_score,
                pos_reasons      = [],
                neg_reasons      = [],
                context_available = False,
            )
        else:
            synergy = compute_synergy(profile, team_profile)
            threat  = compute_threat(profile, enemy_profile)
            ds_v2   = compute_draft_score_v2(rec.avg_score, synergy, threat)

            pos = synergy_reasons(profile, team_profile, synergy)
            neg = threat_reasons(profile, enemy_profile, threat)

            ctx = DraftContextScore(
                champion         = champ_name,
                pick_value       = rec.avg_score,
                synergy          = synergy,
                threat           = threat,
                draft_score_v2   = ds_v2,
                pos_reasons      = pos,
                neg_reasons      = neg,
                context_available = True,
            )

        scores[champ_name.lower()] = ctx

    return DraftContextResult(
        scores         = scores,
        team_profile   = team_profile,
        enemy_profile  = enemy_profile,
        ally_coverage  = team_profile.count,
        enemy_coverage = enemy_profile.count,
    )
