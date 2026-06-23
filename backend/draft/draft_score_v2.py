"""
backend/draft/draft_score_v2.py — Fórmula de Draft Score contextual v2.

Fórmula
-------
DraftScore = 0.70 × PickValue
           + 0.20 × SynergyNorm
           + 0.10 × ThreatNorm

Donde:
  SynergyNorm : synergy (0-20) normalizado a 0-100
  ThreatNorm  : threat (-20 a 0) normalizado a 0-100
                (−20 → 0, 0 → 100)

Resultado: 0-100
"""

from __future__ import annotations


def compute_draft_score_v2(
    pick_value:   float,   # 0-100  (DraftScore v1 / Pick Value)
    synergy:      float,   # 0-20
    threat:       float,   # -20 to 0
) -> float:
    """
    Calcula el Draft Score contextual v2 en escala 0-100.

    Parámetros
    ----------
    pick_value : score histórico del campeón (0-100)
    synergy    : puntuación de sinergia con aliados (0-20)
    threat     : penalización de amenaza enemiga (-20 a 0)

    Retorna
    -------
    float en [0, 100]
    """
    synergy_norm = (synergy / 20.0) * 100.0
    threat_norm  = ((threat + 20.0) / 20.0) * 100.0

    raw = (
        0.70 * pick_value
        + 0.20 * synergy_norm
        + 0.10 * threat_norm
    )
    return round(max(0.0, min(100.0, raw)), 1)
