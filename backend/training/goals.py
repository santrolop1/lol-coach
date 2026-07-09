"""
Selección de skill activo y construcción del Skill Tree.
El orden de prioridad se deriva del Priority Engine, no está hardcodeado.
"""
from __future__ import annotations
import statistics
from .rules import SKILL_CATALOG, ROLE_PROGRESSION

# Mapa de claves del Priority Engine → skill key del Training Engine
_PRIORITY_TO_SKILL: dict[str, str] = {
    "deaths":             "survival",
    "cs_pm":              "farming",
    "kill_participation": "impact",
    "obj_pm":             "pressure",
    "damage_pm":          "impact",
    "vision_pm":          "consistency",
}

# Mapa de dimensión scorer_v2 → skill key
_DIM_TO_SKILL: dict[str, str] = {
    "Positioning":    "survival",
    "Survival":       "survival",
    "Economy":        "farming",
    "Lane Control":   "farming",
    "Combat Impact":  "impact",
    "Pressure":       "pressure",
}


def select_skill(
    priorities: list,
    role: str,
    completed_skill_keys: list[str],
    benchmarks,
) -> str:
    """
    Elige la skill en la que el jugador debe enfocarse.
    Orden de preferencia:
      1. Priority Engine (impacto más alto que no esté completado recientemente)
      2. Dimension más baja de scorer_v2
      3. Primer slot de la progresión del rol
    """
    progression = ROLE_PROGRESSION.get(role.upper(), ROLE_PROGRESSION["ADC"])
    available   = [k for k in progression if k in SKILL_CATALOG and SKILL_CATALOG[k]["roles"]]

    # 1. Priority Engine
    for p in sorted(priorities, key=lambda x: -getattr(x, "impact_score", 0)):
        skill = _PRIORITY_TO_SKILL.get(p.metric_key)
        if skill and skill in available and skill not in completed_skill_keys[-3:]:
            return skill

    # 2. Dimensión más baja desde benchmarks (si disponibles)
    if benchmarks is not None:
        dim_scores: list[tuple[float, str]] = []
        for dim_key, skill_key in _DIM_TO_SKILL.items():
            if skill_key not in available:
                continue
            metric_key = SKILL_CATALOG[skill_key]["primary_metric"]
            stats = benchmarks.metrics.get(metric_key)
            if stats and stats.mean is not None:
                # score bajo = mayor prioridad
                direction = SKILL_CATALOG[skill_key]["direction"]
                if direction == "less_than":
                    dim_scores.append((stats.mean, skill_key))   # alto = malo
                else:
                    dim_scores.append((-stats.mean, skill_key))  # bajo = malo
        if dim_scores:
            dim_scores.sort()
            candidate = dim_scores[0][1]
            if candidate not in completed_skill_keys[-3:]:
                return candidate

    # 3. Fallback: primer skill de la progresión no completado
    for sk in progression:
        if sk not in completed_skill_keys:
            return sk

    return progression[0]


def build_skill_tree(
    scored: list[tuple],    # list[(match_dict, MatchScore)]
    dim_averages: dict[str, float],  # dimension_name → avg_score from analyze_player
    role: str,
    priorities: list,
    completed_skill_keys: list[str],
    active_skill_key: str | None,
) -> list:
    """
    Construye el Skill Tree: lista de SkillNode con score y status.
    """
    from .models import SkillNode

    progression = ROLE_PROGRESSION.get(role.upper(), ROLE_PROGRESSION["ADC"])

    # Calcular consistency score desde std de overall_scores
    overall_scores = [
        ms.overall_score for _, ms in scored
        if ms is not None and ms.overall_score is not None
    ]
    consistency_score: float | None = None
    if len(overall_scores) >= 5:
        mean = statistics.mean(overall_scores)
        std  = statistics.stdev(overall_scores)
        cv   = std / mean if mean > 0 else 1.0
        # cv bajo = buena consistencia; mapear a 0-100 (cv=0 → 100, cv=0.5 → 50)
        consistency_score = round(max(0.0, min(100.0, 100.0 - cv * 200)), 1)

    # Prioridades del Priority Engine para ordenar
    priority_map: dict[str, int] = {}
    for i, p in enumerate(sorted(priorities, key=lambda x: -getattr(x, "impact_score", 0))):
        skill = _PRIORITY_TO_SKILL.get(p.metric_key)
        if skill and skill not in priority_map:
            priority_map[skill] = i + 1

    nodes: list[SkillNode] = []
    for pos, skill_key in enumerate(progression):
        cfg = SKILL_CATALOG.get(skill_key)
        if cfg is None:
            continue

        # Score de la dimensión correspondiente
        dim_key    = cfg["dim_key"] if role.upper() == "ADC" else cfg.get("dim_key_top", cfg["dim_key"])
        base_score = dim_averages.get(dim_key)
        if skill_key == "consistency":
            base_score = consistency_score
        score  = round(base_score, 1) if base_score is not None else 0.0
        conf   = min(0.9, len(scored) / 30.0)

        # Status
        if skill_key in completed_skill_keys:
            status = "completed"
        elif skill_key == active_skill_key:
            status = "active"
        elif pos == 0 or progression[pos - 1] in completed_skill_keys:
            status = "available"
        else:
            status = "locked"

        priority = priority_map.get(skill_key, SKILL_CATALOG[skill_key]["base_priority"])

        nodes.append(SkillNode(
            key            = skill_key,
            name           = cfg["name"],
            description    = cfg["description"],
            score          = score,
            confidence     = round(conf, 2),
            status         = status,
            priority       = priority,
            dim_key        = dim_key,
            primary_metric = cfg["primary_metric"],
        ))

    return nodes
