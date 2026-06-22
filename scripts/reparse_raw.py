"""
scripts/reparse_raw.py — Reparseo de partidas desde archivos locales.

Rellena los campos V2 en la tabla `match` sin realizar ninguna llamada a Riot API.
Lee únicamente los JSONs almacenados en data/raw/.

Uso:
    python scripts/reparse_raw.py

Requisitos:
    - La DB debe existir (ejecutar la app al menos una vez o `python db.py`).
    - El PUUID debe estar configurado en la DB (haber verificado cuenta).
    - Los archivos en data/raw/ deben ser JSONs válidos de Match-V5.
"""

import json
import sys
from pathlib import Path

# Añadir el root del proyecto al path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import db
from parser import parse_match


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

RAW_DIR = ROOT / "data" / "raw"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> dict | None:
    """Carga un JSON de disco. Devuelve None si falla."""
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  ⚠ No se pudo leer {path.name}: {e}")
        return None


def _get_match_id(match_json: dict) -> str | None:
    """Extrae el match_id del JSON."""
    try:
        return match_json["metadata"]["matchId"]
    except KeyError:
        return None


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("  REPARSEO V2 — LoL Coach")
    print("=" * 60)

    # 1. Verificar que existe el directorio de raw
    if not RAW_DIR.exists():
        print(f"\n✗ No existe el directorio: {RAW_DIR}")
        print("  Descarga partidas primero desde la app.")
        sys.exit(1)

    json_files = sorted(RAW_DIR.glob("*.json"))
    if not json_files:
        print(f"\n✗ No hay archivos JSON en: {RAW_DIR}")
        sys.exit(1)

    print(f"\n→ Directorio:  {RAW_DIR}")
    print(f"→ Archivos:    {len(json_files)} JSONs encontrados")

    # 2. Obtener PUUID desde la DB
    puuid = db.get_config("puuid")
    if not puuid:
        print("\n✗ No hay PUUID configurado en la base de datos.")
        print("  Verifica tu cuenta en la app primero (Configuración → Verificar).")
        sys.exit(1)

    print(f"→ PUUID:       {puuid[:16]}...")

    # 3. Asegurar que el schema V2 existe
    db.init_db()
    print("→ Schema V2:   OK (migraciones aplicadas)")

    # 4. Reparsear cada archivo
    print("\n─── Procesando archivos ───────────────────────────────")

    stats = {
        "total_files":    len(json_files),
        "parse_ok":       0,
        "parse_skip":     0,   # puuid no encontrado en la partida
        "parse_error":    0,   # JSON inválido
        "db_updated":     0,   # registros actualizados en DB
        "db_not_found":   0,   # match_id no estaba en DB (partida no descargada)
        "v2_fields_sum":  0,   # suma de campos V2 extraídos (para promedio)
    }

    for json_path in json_files:
        match_json = _load_json(json_path)
        if match_json is None:
            stats["parse_error"] += 1
            continue

        match_id = _get_match_id(match_json)
        if not match_id:
            print(f"  ⚠ {json_path.name}: sin match_id en metadata")
            stats["parse_error"] += 1
            continue

        # Parsear con el parser actualizado
        match_data = parse_match(match_json, puuid)
        if match_data is None:
            # El jugador no está en esta partida (puede ser un JSON de otro jugador)
            stats["parse_skip"] += 1
            continue

        stats["parse_ok"] += 1

        # Extraer solo los campos V2 (no sobreescribir V1 que ya existe)
        v2_fields = match_data.to_v2_fields()
        stats["v2_fields_sum"] += len(v2_fields)

        # Actualizar en DB
        if db.match_exists(match_id):
            updated = db.update_match_v2(match_id, v2_fields)
            if updated:
                stats["db_updated"] += 1
            # Si no se actualizó, es porque los campos ya estaban bien
        else:
            stats["db_not_found"] += 1
            # La partida no está en DB → no insertar aquí (solo reparse, no import)

    # 5. Reporte
    print("\n─── Resultado ─────────────────────────────────────────")
    print(f"  Archivos procesados:     {stats['total_files']}")
    print(f"  Parseados OK:            {stats['parse_ok']}")
    print(f"  Saltados (sin PUUID):    {stats['parse_skip']}")
    print(f"  Error de lectura:        {stats['parse_error']}")
    print(f"  Actualizados en DB:      {stats['db_updated']}")
    print(f"  No estaban en DB:        {stats['db_not_found']}")

    if stats["parse_ok"] > 0:
        avg_v2 = stats["v2_fields_sum"] / stats["parse_ok"]
        print(f"  Campos V2 prom/partida:  {avg_v2:.1f} / 26")

    if stats["db_updated"] > 0:
        print(f"\n✓ Reparseo completado: {stats['db_updated']} partidas actualizadas con campos V2.")
    elif stats["parse_ok"] > 0 and stats["db_not_found"] == stats["parse_ok"]:
        print("\n⚠ Ninguna partida del JSON coincide con partidas en la DB.")
        print("  Descarga las partidas desde la app antes de reparsear.")
    else:
        print("\n✓ No hubo cambios — los campos V2 ya estaban al día.")


if __name__ == "__main__":
    main()
