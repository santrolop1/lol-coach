"""
scripts/test_scorer_v2.py — Pruebas del motor de scoring V2 con datos reales de SQLite.

Muestra:
  - Score ADC (últimas 5 partidas)
  - Score TOP (única partida disponible)
  - Overall Score del jugador
  - Problema principal detectado
  - Tendencia
  - Consistencia
  - Confidence Level
  - Benchmarks calculados desde datos reales
  - Limitaciones detectadas

Uso:
    python scripts/test_scorer_v2.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import db
import scorer_v2 as sv2


# ---------------------------------------------------------------------------
# Helpers de formato
# ---------------------------------------------------------------------------

def _bar(score, width=20):
    """Barra visual para un score 0-100."""
    if score is None:
        return "[    N/A    ]"
    filled = int(score / 100 * width)
    return "[" + "=" * filled + "-" * (width - filled) + f"] {score:.1f}"


def _sep(char="─", width=66):
    return char * width


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 66)
    print("  TEST SCORER V2 — LoL Coach")
    print("  Datos reales desde SQLite")
    print("=" * 66)

    # Cargar todas las partidas
    puuid = db.get_config("puuid")
    if not puuid:
        print("Sin PUUID configurado. Ejecuta la app primero.")
        sys.exit(1)

    all_matches = db.get_matches(puuid, limit=200)
    adc_matches = [m for m in all_matches if m["role"] == "ADC"]
    top_matches = [m for m in all_matches if m["role"] == "TOP"]

    print(f"\n  Total partidas cargadas: {len(all_matches)}")
    print(f"  ADC: {len(adc_matches)}   TOP: {len(top_matches)}")

    # =========================================================================
    # ANÁLISIS ADC
    # =========================================================================
    print(f"\n{'=' * 66}")
    print("  ANÁLISIS ADC")
    print("=" * 66)

    result_adc = sv2.analyze_player(all_matches, "ADC")

    print(f"\n  Overall Score ADC:   {_bar(result_adc.overall_score)}")
    print(f"  Confidence Level:    {result_adc.confidence_level.upper()} (N={result_adc.sample_size})")
    print(f"  Surrenders:          {result_adc.surrender_count}")

    print(f"\n  {'─'*62}")
    print("  DIMENSIONES (promedio sobre todas las partidas):")
    print(f"  {'─'*62}")
    for dim_name, dim_score in result_adc.dimensions.items():
        marker = " ← PROBLEMA PRINCIPAL" if dim_name == result_adc.primary_problem else ""
        print(f"  {dim_name:<20} {_bar(dim_score)}{marker}")

    print(f"\n  Problema principal: {result_adc.primary_problem}")

    print(f"\n  {'─'*62}")
    print("  TENDENCIA:")
    print(f"  {'─'*62}")
    trend_icon = {"improving": "↑", "stable": "→", "declining": "↓"}.get(result_adc.trend, "?")
    print(f"  Tendencia:     {trend_icon} {result_adc.trend.upper()}")
    print(f"  Pendiente OLS: {result_adc.trend_slope:+.3f} pts/partida")
    print(f"  Consistencia:  {result_adc.consistency_score:.1f}/100" if result_adc.consistency_score else "  Consistencia:  N/A")
    print(f"  (Método: CV = std/mean × 100 → consistency = max(0, 100 - CV))")

    # Últimas 5 partidas ADC
    print(f"\n  {'─'*62}")
    print("  ÚLTIMAS 5 PARTIDAS ADC:")
    print(f"  {'─'*62}")
    recent_5 = sorted(result_adc.match_scores, key=lambda ms: ms.played_at, reverse=True)[:5]
    print(f"  {'Fecha':<12} {'Camp':<14} {'Res':<6} {'Surr':<5} {'Overall':>8}  {'Econ':>6}  {'Posit':>6}  {'Combat':>7}")
    print(f"  {'─'*12} {'─'*14} {'─'*6} {'─'*5} {'─'*8}  {'─'*6}  {'─'*6}  {'─'*7}")
    for ms in recent_5:
        date = ms.played_at[:10]
        surr = "YES" if ms.is_surrender else "no"
        dim_scores = {d.name: d.score for d in ms.dimensions}
        econ    = f"{dim_scores.get('Economy', 0):.0f}"    if dim_scores.get('Economy') else "N/A"
        posit   = f"{dim_scores.get('Positioning', 0):.0f}" if dim_scores.get('Positioning') else "N/A"
        combat  = f"{dim_scores.get('Combat Impact', 0):.0f}" if dim_scores.get('Combat Impact') else "N/A"
        overall = f"{ms.overall_score:.0f}" if ms.overall_score is not None else "N/A"
        print(f"  {date:<12} {ms.champion:<14} {ms.result:<6} {surr:<5} {overall:>8}  {econ:>6}  {posit:>6}  {combat:>7}")

    # Benchmarks ADC
    print(f"\n  {'─'*62}")
    print("  BENCHMARKS ADC (auto-relativos, desde datos reales):")
    print(f"  {'─'*62}")
    bm = result_adc.benchmarks
    bm_fields = [
        ("cs_per_min",         "CS/min"),
        ("cs_at_10",           "CS@10"),
        ("gold_per_min",       "Gold/min"),
        ("deaths",             "Muertes"),
        ("time_dead_pct",      "% tiempo muerto"),
        ("kill_participation", "Kill Participation"),
        ("team_damage_pct",    "Team Dmg %"),
        ("objectives_per_min", "Objectives/min"),
    ]
    print(f"  {'Métrica':<24} {'N':>4}  {'P25':>8}  {'P50':>8}  {'P75':>8}  {'P90':>8}")
    print(f"  {'─'*24} {'─'*4}  {'─'*8}  {'─'*8}  {'─'*8}  {'─'*8}")
    for key, label in bm_fields:
        if key in bm.metrics:
            s = bm.metrics[key]
            print(f"  {label:<24} {s.n:>4}  {s.p25:>8.2f}  {s.p50:>8.2f}  {s.p75:>8.2f}  {s.p90:>8.2f}")
        else:
            print(f"  {label:<24} {'N/A':>4}")

    print(f"\n  Nota: {bm.note}")

    # =========================================================================
    # ANÁLISIS TOP
    # =========================================================================
    print(f"\n{'=' * 66}")
    print("  ANÁLISIS TOP")
    print("=" * 66)

    result_top = sv2.analyze_player(all_matches, "TOP")

    print(f"\n  Overall Score TOP:   {_bar(result_top.overall_score)}")
    print(f"  Confidence Level:    {result_top.confidence_level.upper()} (N={result_top.sample_size})")

    print(f"\n  DIMENSIONES TOP:")
    for dim_name, dim_score in result_top.dimensions.items():
        marker = " ← PROBLEMA PRINCIPAL" if dim_name == result_top.primary_problem else ""
        print(f"  {dim_name:<20} {_bar(dim_score)}{marker}")

    if result_top.match_scores:
        ms = result_top.match_scores[0]
        print(f"\n  Partida TOP analizada:")
        print(f"    Campeón:  {ms.champion}")
        print(f"    Resultado: {ms.result}")
        print(f"    Fecha:    {ms.played_at[:10]}")
        for d in ms.dimensions:
            print(f"    {d.name}: {d.score}")
            for k, v in d.metrics.items():
                print(f"      {k}: {v}")
            for note in d.notes:
                print(f"      [NOTA] {note}")

    # =========================================================================
    # VERIFICACIÓN MATEMÁTICA
    # =========================================================================
    print(f"\n{'=' * 66}")
    print("  VERIFICACIÓN MATEMÁTICA")
    print("=" * 66)

    # Test de tendencia
    print("\n  Test de tendencia (regresión lineal OLS):")
    cases = [
        ("Mejora constante",  [30, 40, 50, 60, 70, 80]),
        ("Deterioro",         [80, 70, 60, 50, 40, 30]),
        ("Estable",           [58, 62, 55, 60, 58, 61]),
        ("Jugador A (errático)", [90, 90, 90, 10, 10]),
        ("Jugador B (plateau)",  [58, 58, 58, 58, 58]),
    ]
    for label, scores in cases:
        slope = sv2._linear_slope(scores)
        trend = sv2._classify_trend(slope)
        consistency = sv2._consistency_cv(scores)
        print(f"  {label:<30} slope={slope:+.2f}  trend={trend:<10}  consistency={consistency:.1f}")

    # Test de consistencia CV
    print("\n  Test de consistencia (Coefficient of Variation):")
    print("  [90, 90, 90, 10, 10]:", sv2._consistency_cv([90, 90, 90, 10, 10]))
    print("  [58, 58, 58, 58, 58]:", sv2._consistency_cv([58, 58, 58, 58, 58]))
    print("  [40, 60, 40, 60, 40]:", sv2._consistency_cv([40, 60, 40, 60, 40]))

    # Test de confidence
    print("\n  Test de confidence level:")
    for n in [0, 3, 7, 15, 25]:
        print(f"  N={n:>3}: {sv2._confidence_level(n)}")

    # =========================================================================
    # LIMITACIONES DETECTADAS
    # =========================================================================
    print(f"\n{'=' * 66}")
    print("  LIMITACIONES DETECTADAS")
    print("=" * 66)
    print("\n  ADC:")
    for lim in result_adc.limitations:
        print(f"  [!] {lim}")
    print("\n  TOP:")
    for lim in result_top.limitations:
        print(f"  [!] {lim}")

    print(f"\n{'=' * 66}")
    print("  RIESGOS FUTUROS")
    print("=" * 66)
    risks = [
        "Scores son auto-relativos. Un jugador que siempre juega mal tendrá "
        "scores de 50 en todo. Sin benchmarks de elo, no hay calibración externa.",

        "team_damage_pct no discrimina win/loss en este dataset (delta=-0.001). "
        "Con N>100 partidas puede revisarse su peso. Por ahora tiene peso igual.",

        "Surrenders con game_ended_surrender=1 están incluidos. Si el jugador "
        "tiene muchas rendidas, las métricas de combat/objectives estarán sesgadas "
        "hacia valores bajos (menos tiempo de juego = menos daño total).",

        "Los benchmarks TOP son no-calculables con N=1. Cualquier score TOP "
        "es 50.0 para todas las métricas (auto-referencia degenerada).",

        "Sin Challenges API integrada, los benchmarks son solo auto-relativos. "
        "Para comparación con otros jugadores del mismo elo, se necesita "
        "/lol/challenges/v1/challenges/{id}/percentiles (no implementado).",

        "Cambios de meta (patches) no se modelan. Un buff a ADC de farm "
        "subiría los cs_at_10 de toda la playerbase pero el sistema "
        "seguiría usando la distribución histórica del jugador como referencia.",
    ]
    for i, risk in enumerate(risks, 1):
        print(f"\n  Riesgo {i}: {risk}")

    print(f"\n{'=' * 66}")
    print("  Sprint 2.1 completado.")
    print("=" * 66)


if __name__ == "__main__":
    main()
