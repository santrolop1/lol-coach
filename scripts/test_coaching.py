"""
scripts/test_coaching.py — Pruebas del coaching engine con datos reales de SQLite.

Muestra:
  - Coaching ADC completo con todos los campos de CoachingResult
  - Coaching TOP (datos insuficientes — comportamiento esperado)
  - Ejemplos de evidencia con números reales

Uso:
    python scripts/test_coaching.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import db
import scorer_v2 as sv2
import coaching_engine as ce


# ---------------------------------------------------------------------------
# Helpers de formato
# ---------------------------------------------------------------------------

def _sep(char="─", width=68):
    return char * width


def _wrap(text: str, indent: int = 4, width: int = 68) -> str:
    """Ajuste de línea simple para textos largos."""
    prefix = " " * indent
    words  = text.split()
    lines  = []
    line   = prefix
    for word in words:
        if len(line) + len(word) + 1 > width:
            lines.append(line)
            line = prefix + word
        else:
            line = (line + " " + word) if line.strip() else prefix + word
    if line.strip():
        lines.append(line)
    return "\n".join(lines)


def _print_section(title: str):
    print(f"\n  {_sep('-', 64)}")
    print(f"  {title}")
    print(f"  {_sep('-', 64)}")


def _print_coaching(result: ce.CoachingResult):
    """Imprime un CoachingResult completo de forma legible."""

    print(f"\n{'=' * 68}")
    print(f"  COACHING {result.role}  |  Confianza: {result.confidence_level.upper()}  |  N={result.sample_size}")
    print(f"{'=' * 68}")

    # Session warning
    if result.session_warning:
        print(f"\n  [!] ALERTA DE SESION")
        print(_wrap(result.session_warning, 6))

    # Problema principal
    _print_section("PROBLEMA PRINCIPAL")
    print(f"  >> {result.primary_problem}")
    print()
    print(_wrap(result.evidence, 6))

    _print_section("CAUSA PROBABLE")
    print(_wrap(result.probable_cause, 6))

    _print_section("IMPACTO")
    print(_wrap(result.impact, 6))

    # Objetivo semanal
    _print_section("OBJETIVO SEMANAL (unico)")
    wg = result.weekly_goal
    print(f"  >> {wg.description}")
    print(f"     Metrica:  {wg.metric}")
    print(f"     Actual:   {wg.current:.2f}")
    print(f"     Objetivo: {wg.target:.2f}")
    print(f"     Plazo:    {wg.window}")

    # Plan de entrenamiento
    _print_section("PLAN DE ENTRENAMIENTO")
    tp = result.training_plan
    print(f"  [1 PRINCIPAL]")
    print(_wrap(tp.primary, 6))
    for i, sec in enumerate(tp.secondary, start=2):
        print(f"\n  [{i} SECUNDARIO]")
        print(_wrap(sec, 6))

    # Fortalezas
    _print_section("FORTALEZAS (max 3)")
    if result.strengths:
        for i, s in enumerate(result.strengths, start=1):
            print(f"  {i}. {s.name}")
            print(_wrap(s.evidence, 6))
    else:
        print("  Sin fortalezas detectadas con los datos disponibles.")

    # Mejoras secundarias
    _print_section("MEJORAS SECUNDARIAS DETECTADAS")
    if result.improvements:
        for imp in result.improvements:
            print(f"  - {imp}")
    else:
        print("  Sin problemas secundarios detectados.")

    # Tendencia
    _print_section("RESUMEN DE PROGRESO Y TENDENCIA")
    print(_wrap(result.trend_summary, 6))

    print(f"\n{'=' * 68}\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 68)
    print("  TEST COACHING ENGINE — LoL Coach")
    print("  Datos reales desde SQLite")
    print("=" * 68)

    puuid = db.get_config("puuid")
    if not puuid:
        print("Sin PUUID configurado. Ejecuta la app primero.")
        sys.exit(1)

    all_matches = db.get_matches(puuid, limit=200)
    adc_matches = [m for m in all_matches if m["role"] == "ADC"]
    top_matches = [m for m in all_matches if m["role"] == "TOP"]

    print(f"\n  Partidas cargadas: {len(all_matches)}")
    print(f"  ADC: {len(adc_matches)}   TOP: {len(top_matches)}")

    # =========================================================================
    # SCORE RESULTS (input para el coaching engine)
    # =========================================================================
    print(f"\n  Calculando ScoreResultV2 para ADC y TOP...")
    score_adc = sv2.analyze_player(all_matches, "ADC")
    score_top = sv2.analyze_player(all_matches, "TOP")

    print(f"  ADC: overall={score_adc.overall_score}  N={score_adc.sample_size}  confidence={score_adc.confidence_level}")
    print(f"  TOP: overall={score_top.overall_score}  N={score_top.sample_size}  confidence={score_top.confidence_level}")

    # =========================================================================
    # COACHING ADC
    # =========================================================================
    print(f"\n  Ejecutando coaching ADC...")
    coaching_adc = ce.analyze_coaching(score_adc, all_matches, "ADC")
    _print_coaching(coaching_adc)

    # =========================================================================
    # COACHING TOP
    # =========================================================================
    print(f"\n  Ejecutando coaching TOP...")
    coaching_top = ce.analyze_coaching(score_top, all_matches, "TOP")
    _print_coaching(coaching_top)

    # =========================================================================
    # VERIFICACIÓN DE INTEGRIDAD
    # =========================================================================
    print("=" * 68)
    print("  VERIFICACION DE INTEGRIDAD")
    print("=" * 68)

    checks = [
        ("ADC tiene primary_problem", bool(coaching_adc.primary_problem)),
        ("ADC tiene evidence con numeros", any(c.isdigit() for c in coaching_adc.evidence)),
        ("ADC tiene weekly_goal.current > 0", coaching_adc.weekly_goal.current > 0),
        ("ADC tiene weekly_goal.target definido", coaching_adc.weekly_goal.target >= 0),
        ("ADC tiene training_plan.primary", bool(coaching_adc.training_plan.primary)),
        ("ADC tiene 2 secondary actions", len(coaching_adc.training_plan.secondary) == 2),
        ("ADC strengths <= 3", len(coaching_adc.strengths) <= 3),
        ("ADC improvements es lista", isinstance(coaching_adc.improvements, list)),
        ("ADC trend_summary no vacia", bool(coaching_adc.trend_summary)),
        ("ADC confidence_level valido", coaching_adc.confidence_level in ("insufficient", "preliminary", "reliable", "robust")),
        ("TOP confidence_level es insufficient (N=1)", coaching_top.confidence_level == "insufficient"),
        ("TOP devuelve CoachingResult valido", isinstance(coaching_top, ce.CoachingResult)),
    ]

    passed = 0
    for label, condition in checks:
        status = "OK" if condition else "FAIL"
        print(f"  [{status}] {label}")
        if condition:
            passed += 1

    print(f"\n  Resultado: {passed}/{len(checks)} checks pasados.")

    # =========================================================================
    # RESUMEN EJECUTIVO PARA LA UI
    # =========================================================================
    print(f"\n{'=' * 68}")
    print("  RESUMEN EJECUTIVO (mock para futuro UI)")
    print("=" * 68)
    print(f"\n  PROBLEMA PRINCIPAL ADC : {coaching_adc.primary_problem}")
    print(f"  OBJETIVO SEMANAL ADC   : {coaching_adc.weekly_goal.description}")
    print(f"  ACCION HOY             : {coaching_adc.training_plan.primary[:80]}...")

    if coaching_adc.session_warning:
        print(f"\n  ALERTA                 : {coaching_adc.session_warning[:80]}...")

    if coaching_adc.strengths:
        print(f"\n  FORTALEZA PRINCIPAL    : {coaching_adc.strengths[0].name}")

    print(f"\n{'=' * 68}")
    print("  Sprint 3 completado.")
    print("=" * 68)


if __name__ == "__main__":
    main()
