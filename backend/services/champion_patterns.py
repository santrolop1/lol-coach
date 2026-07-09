"""
backend/services/champion_patterns.py — Detección de patrones por campeón.

Analiza splits win/loss dentro de las partidas de un mismo campeón
y genera ChampionPattern con datos reales.

Umbrales:
  DEATHS_PCT   +20% muertes en derrotas vs victorias → patrón  (≥35% → crítico)
  FARM_PCT     -15% CS/min en derrotas vs victorias  → patrón  (≥25% → crítico)
  DAMAGE_PCT   -20% daño/min en derrotas vs victorias→ patrón  (≥30% → crítico)
  KP_PCT       -15% KP en derrotas vs victorias      → patrón  (≥25% → crítico)
  CONSIST_CV   coeficiente de variación ≥ 0.35       → patrón de inconsistencia
"""

from __future__ import annotations

from .champion_models import ChampionAnalysis, ChampionPattern

# ── Umbrales ─────────────────────────────────────────────────────────────────

_DEATHS_WARN     = 20.0
_DEATHS_CRIT     = 35.0
_FARM_WARN       = 15.0
_FARM_CRIT       = 25.0
_DAMAGE_WARN     = 20.0
_DAMAGE_CRIT     = 30.0
_KP_WARN         = 15.0
_KP_CRIT         = 25.0
_CONSIST_WARN    = 0.35   # CV
_CONSIST_CRIT    = 0.50


def detect_patterns(analysis: ChampionAnalysis) -> list[ChampionPattern]:
    """
    Detecta todos los patrones significativos en el rendimiento del campeón.

    Requiere al menos 2 victorias Y 2 derrotas para generar patrones de split.
    El patrón de consistencia solo requiere ≥ 4 partidas y score_std disponible.

    Retorna la lista ordenada: críticos primero, luego warnings.
    """
    patterns: list[ChampionPattern] = []

    has_split = analysis.wins >= 2 and analysis.losses >= 2

    if has_split:
        # ── 1. Muertes ────────────────────────────────────────────────────────
        delta = analysis.deaths_win_loss_delta_pct
        if delta >= _DEATHS_WARN:
            sev = "critical" if delta >= _DEATHS_CRIT else "warning"
            patterns.append(ChampionPattern(
                pattern_type = "deaths",
                title        = "Muertes elevadas en derrotas",
                description  = (
                    f"Tus derrotas con {analysis.champion_name} tienen "
                    f"{delta:.0f}% más muertes "
                    f"({analysis.loss_avg_deaths:.1f} vs "
                    f"{analysis.win_avg_deaths:.1f} en victorias)."
                ),
                severity     = sev,
                metric_delta = delta,
            ))

        # ── 2. Farm ───────────────────────────────────────────────────────────
        cs_delta = analysis.cs_win_loss_delta_pct   # negativo = menos CS en derrotas
        if cs_delta <= -_FARM_WARN:
            sev = "critical" if cs_delta <= -_FARM_CRIT else "warning"
            patterns.append(ChampionPattern(
                pattern_type = "farm",
                title        = "Farm cae en derrotas",
                description  = (
                    f"Tu CS/min con {analysis.champion_name} cae "
                    f"{abs(cs_delta):.0f}% en derrotas "
                    f"({analysis.loss_avg_cs_min:.1f} vs "
                    f"{analysis.win_avg_cs_min:.1f} en victorias)."
                ),
                severity     = sev,
                metric_delta = abs(cs_delta),
            ))

        # ── 3. Daño ───────────────────────────────────────────────────────────
        dmg_delta = analysis.damage_win_loss_delta_pct
        if dmg_delta <= -_DAMAGE_WARN and analysis.win_avg_damage_min > 0:
            sev = "critical" if dmg_delta <= -_DAMAGE_CRIT else "warning"
            patterns.append(ChampionPattern(
                pattern_type = "damage",
                title        = "Daño reducido en derrotas",
                description  = (
                    f"Tu daño/min con {analysis.champion_name} cae "
                    f"{abs(dmg_delta):.0f}% en derrotas "
                    f"({analysis.loss_avg_damage_min:.0f} vs "
                    f"{analysis.win_avg_damage_min:.0f} en victorias)."
                ),
                severity     = sev,
                metric_delta = abs(dmg_delta),
            ))

        # ── 4. Kill participation ─────────────────────────────────────────────
        kp_delta = analysis.kp_win_loss_delta_pct
        if (
            kp_delta <= -_KP_WARN
            and analysis.win_avg_kp > 0
            and analysis.loss_avg_kp > 0
        ):
            sev = "critical" if kp_delta <= -_KP_CRIT else "warning"
            patterns.append(ChampionPattern(
                pattern_type = "kp",
                title        = "Baja participación en derrotas",
                description  = (
                    f"Tu participación en peleas con {analysis.champion_name} "
                    f"cae {abs(kp_delta):.0f}% en derrotas "
                    f"({analysis.loss_avg_kp:.0%} vs "
                    f"{analysis.win_avg_kp:.0%} en victorias)."
                ),
                severity     = sev,
                metric_delta = abs(kp_delta),
            ))

    # ── 5. Consistencia ───────────────────────────────────────────────────────
    if analysis.games >= 4 and analysis.score_std > 0:
        cv = analysis.consistency_cv
        if cv >= _CONSIST_WARN:
            sev = "critical" if cv >= _CONSIST_CRIT else "warning"
            patterns.append(ChampionPattern(
                pattern_type = "consistency",
                title        = "Alto grado de inconsistencia",
                description  = (
                    f"Tus {analysis.games} partidas con {analysis.champion_name} "
                    f"muestran alta variabilidad de rendimiento "
                    f"(score σ = {analysis.score_std:.1f})."
                ),
                severity     = sev,
                metric_delta = round(cv * 100, 1),
            ))

    # Ordenar: críticos primero, luego por magnitud
    patterns.sort(key=lambda p: (0 if p.severity == "critical" else 1, -p.metric_delta))
    return patterns
