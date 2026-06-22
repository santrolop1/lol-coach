"""
scripts/validate_v2.py — Validación de completitud de campos V2 en SQLite.

Muestra:
  - Total de partidas en DB
  - % de campos V2 clave completados
  - Detalle por campo
  - Alertas de problemas detectados

Uso:
    python scripts/validate_v2.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import db


# ---------------------------------------------------------------------------
# Campos a validar con su descripción
# ---------------------------------------------------------------------------

# (campo_db, etiqueta, crítico)
# crítico=True → aparece en el resumen ejecutivo
_FIELDS_TO_CHECK: list[tuple[str, str, bool]] = [
    # Críticos para Coaching Engine
    ("vision_score",         "Vision Score",              True),
    ("kill_participation",   "Kill Participation",        True),
    ("cs_at_10",             "CS@10 (challenges)",        True),
    ("team_damage_pct",      "Team Damage %",             True),
    ("game_ended_surrender", "Surrender Flag",            True),
    # Importantes para Role Engine
    ("control_wards_placed", "Control Wards Placed",      True),
    ("max_cs_advantage",     "Max CS Advantage",          True),
    ("damage_to_objectives", "Damage to Objectives",      False),
    ("damage_to_turrets",    "Damage to Turrets",         False),
    ("damage_taken",         "Damage Taken",              False),
    ("time_spent_dead",      "Time Spent Dead",           False),
    ("longest_time_alive",   "Longest Time Alive",        False),
    ("turret_takedowns",     "Turret Takedowns",          False),
    # Económicos
    ("gold_earned",          "Gold Earned",               False),
    # Visión detallada
    ("wards_placed",         "Wards Placed",              False),
    ("wards_killed",         "Wards Killed",              False),
    ("control_wards_bought", "Control Wards Bought",      False),
    # Utilidad
    ("heals_on_teammates",   "Heals on Teammates",        False),
    ("time_ccing_others",    "Time CCing Others",         False),
    # JGL
    ("baron_kills",          "Baron Kills",               False),
    ("dragon_kills",         "Dragon Kills",              False),
    ("objectives_stolen",    "Objectives Stolen",         False),
    ("enemy_jungle_cs",      "Enemy Jungle CS",           False),
    # Otros
    ("turret_plates_taken",  "Turret Plates Taken",       False),
    ("damage_self_mitigated","Damage Self Mitigated",     False),
    ("first_blood",          "First Blood",               False),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pct(count: int, total: int) -> str:
    if total == 0:
        return "  N/A"
    p = count / total * 100
    bar_len = int(p / 5)
    bar = "█" * bar_len + "░" * (20 - bar_len)
    return f"{p:5.1f}%  [{bar}]"


def _check_field(conn, field: str, total: int) -> int:
    """Cuenta partidas donde el campo no es NULL."""
    row = conn.execute(
        f"SELECT COUNT(*) FROM match WHERE {field} IS NOT NULL"
    ).fetchone()
    return row[0] if row else 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    import sqlite3

    db_path = ROOT / "data" / "lol_coach.db"
    if not db_path.exists():
        print("✗ No existe la base de datos. Ejecuta la app primero.")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # ── Totales generales ────────────────────────────────────────────────────
    total = conn.execute("SELECT COUNT(*) FROM match").fetchone()[0]
    adc   = conn.execute("SELECT COUNT(*) FROM match WHERE role='ADC'").fetchone()[0]
    top   = conn.execute("SELECT COUNT(*) FROM match WHERE role='TOP'").fetchone()[0]
    other = conn.execute("SELECT COUNT(*) FROM match WHERE role='OTHER'").fetchone()[0]

    surrendered = conn.execute(
        "SELECT COUNT(*) FROM match WHERE game_ended_surrender = 1"
    ).fetchone()[0]

    print("=" * 66)
    print("  VALIDACIÓN V2 — LoL Coach")
    print("=" * 66)
    print(f"\n  Total partidas en DB:  {total}")
    print(f"  ADC:  {adc}   TOP:  {top}   OTHER:  {other}")
    if total > 0:
        s_pct = surrendered / total * 100
        print(f"  Rendidas (early):  {surrendered}  ({s_pct:.0f}%)  ← filtrar del análisis")

    if total == 0:
        print("\n  Sin partidas. Descarga partidas desde la app primero.")
        conn.close()
        sys.exit(0)

    # ── Verificar que columnas V2 existen en el schema ──────────────────────
    existing_cols = {
        row[1]
        for row in conn.execute("PRAGMA table_info(match)").fetchall()
    }
    v2_col_names = [f for f, _, _ in _FIELDS_TO_CHECK]
    missing_schema = [f for f in v2_col_names if f not in existing_cols]

    if missing_schema:
        print(f"\n  ⚠ Columnas V2 ausentes del schema ({len(missing_schema)}):")
        for c in missing_schema:
            print(f"     - {c}")
        print("  Ejecuta db.init_db() o arranca la app para aplicar la migración.")
    else:
        print(f"\n  Schema V2: ✓ Las {len(v2_col_names)} columnas V2 existen en la tabla.")

    # ── Detalle por campo ────────────────────────────────────────────────────
    print("\n─── Completitud de campos V2 ────────────────────────────────────")
    print(f"  {'Campo':<26} {'Completas':>9}  {'%':>5}   Barra")
    print("  " + "─" * 62)

    critical_issues: list[str] = []

    for field, label, is_critical in _FIELDS_TO_CHECK:
        if field in missing_schema:
            print(f"  {label:<26} {'[SCHEMA FALTANTE]':>9}")
            continue

        count = _check_field(conn, field, total)
        pct_str = _pct(count, total)
        marker = "★" if is_critical else " "
        print(f"  {marker} {label:<24} {count:>6}/{total:<6}  {pct_str}")

        if is_critical and total > 0 and count / total < 0.80:
            critical_issues.append(
                f"{label}: {count}/{total} ({count/total*100:.0f}%) — esperado ≥80%"
            )

    # ── Resumen ejecutivo ────────────────────────────────────────────────────
    print("\n─── Resumen ejecutivo ───────────────────────────────────────────")

    if not missing_schema and not critical_issues:
        print("  ✓ Schema V2 aplicado correctamente.")
        print("  ✓ Todos los campos críticos tienen cobertura ≥80%.")
        print("  ✓ Sprint 1 completado: datos listos para Role Engine V2.")
    else:
        if missing_schema:
            print(f"  ✗ {len(missing_schema)} columnas sin migrar. Ejecuta la app para aplicar.")
        if critical_issues:
            print(f"  ⚠ {len(critical_issues)} campos críticos con baja cobertura:")
            for issue in critical_issues:
                print(f"     - {issue}")
            print("\n  Acción: ejecuta scripts/reparse_raw.py para rellenar campos V2.")

    # ── Análisis de challenges disponibles ──────────────────────────────────
    print("\n─── Disponibilidad de challenges (depende del parche) ──────────")
    ch_fields = [
        ("kill_participation", "killParticipation"),
        ("team_damage_pct",    "teamDamagePercentage"),
        ("cs_at_10",           "laneMinionsFirst10Minutes"),
        ("max_cs_advantage",   "maxCsAdvantageOnLaneOpponent"),
        ("turret_plates_taken","turretPlatesTaken"),
    ]
    for db_col, api_name in ch_fields:
        if db_col in missing_schema:
            continue
        count = _check_field(conn, db_col, total)
        pct = count / total * 100 if total > 0 else 0
        status = "✓" if pct >= 80 else "⚠"
        print(f"  {status}  challenges.{api_name:<34} {pct:5.1f}%")

    print("\n  Nota: challenges solo existe en partidas de parche 12.x en adelante.")
    print("  Partidas antiguas tendrán estos campos en NULL (comportamiento esperado).")

    # ── Flags críticos ───────────────────────────────────────────────────────
    if "game_ended_surrender" not in missing_schema:
        null_surrender = conn.execute(
            "SELECT COUNT(*) FROM match WHERE game_ended_surrender IS NULL"
        ).fetchone()[0]
        if null_surrender > 0:
            print(f"\n  ⚠ {null_surrender} partidas sin surrender flag.")
            print("    Ejecuta reparse_raw.py para completarlas.")
            print("    Mientras tanto, esas partidas NO se filtrarán del análisis.")

    conn.close()
    print()


if __name__ == "__main__":
    main()
