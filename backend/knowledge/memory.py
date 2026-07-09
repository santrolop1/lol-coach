"""
backend/knowledge/memory.py — Persistencia de objetivos adaptativos.

Usa db.save_config / db.get_config con JSON.
No modifica el esquema SQLite.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import db
from backend.knowledge.models import MemoryEntry

_KEY = "knowledge_memory_v1"


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


# ── Carga / guardado ───────────────────────────────────────────────────────────

def load() -> dict:
    raw = db.get_config(_KEY)
    if not raw:
        return {"goals": [], "last_read_at": None}
    try:
        return json.loads(raw)
    except Exception:
        return {"goals": [], "last_read_at": None}


def _save(mem: dict) -> None:
    db.save_config(_KEY, json.dumps(mem))


# ── Consultas ──────────────────────────────────────────────────────────────────

def get_active(mem: dict) -> dict | None:
    """Devuelve el objetivo activo más reciente, o None."""
    for g in reversed(mem.get("goals", [])):
        if g.get("status") == "active":
            return g
    return None


def recently_targeted_keys(mem: dict, n: int = 3) -> set[str]:
    """Devuelve las metric_key de los últimos N objetivos (evitar repetir)."""
    goals = mem.get("goals", [])
    return {g["metric_key"] for g in goals[-n:]}


def to_memory_entries(mem: dict) -> list[MemoryEntry]:
    entries = []
    for g in reversed(mem.get("goals", [])):
        entries.append(MemoryEntry(
            goal_title=f"{g.get('target_str', '?')} de {g.get('metric_label', '?')}",
            status=g.get("status", "active"),
            created_at=(g.get("created_at") or "")[:10],
            completed_at=(g.get("completed_at") or "")[:10] or None,
            metric_key=g.get("metric_key", ""),
        ))
    return entries[:8]  # mostrar últimos 8


# ── Mutaciones ─────────────────────────────────────────────────────────────────

def complete_goal(mem: dict, goal_id: str) -> None:
    for g in mem.get("goals", []):
        if g.get("id") == goal_id and g.get("status") == "active":
            g["status"] = "completed"
            g["completed_at"] = _now_iso()
    _save(mem)


def add_goal(
    mem: dict,
    metric_key: str,
    metric_label: str,
    target_value: float,
    target_str: str,
    higher_is_better: bool,
) -> dict:
    goal = {
        "id":               str(uuid.uuid4())[:8],
        "metric_key":       metric_key,
        "metric_label":     metric_label,
        "target_value":     target_value,
        "target_str":       target_str,
        "higher_is_better": higher_is_better,
        "check_window":     5,
        "status":           "active",
        "created_at":       _now_iso(),
        "completed_at":     None,
    }
    mem.setdefault("goals", []).append(goal)
    _save(mem)
    return goal


def update_last_read(mem: dict) -> None:
    mem["last_read_at"] = _now_iso()
    _save(mem)
