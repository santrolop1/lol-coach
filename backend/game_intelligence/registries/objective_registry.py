"""ObjectiveRegistry — acceso al conocimiento de Objetivos del mapa."""

from __future__ import annotations
import logging
from typing import Any

from .base import BaseRegistry
from ..models.objective import ObjectiveDefinition, ObjectiveType, Priority

logger = logging.getLogger(__name__)


class ObjectiveRegistry(BaseRegistry):
    """
    Carga y sirve ObjectiveDefinition.
    Fuente: knowledge/objectives/definitions.py → OBJECTIVES
    """

    def _ensure_loaded(self) -> None:
        if "obj:__all__" in self._cache:
            return
        try:
            from ..knowledge.objectives.definitions import OBJECTIVES
            for obj in OBJECTIVES:
                self._cache[self._cache_key("obj", obj.id)] = obj
            self._cache["obj:__all__"] = [o.id for o in OBJECTIVES]
            logger.debug("ObjectiveRegistry: %d objetivos cargados.", len(OBJECTIVES))
        except Exception as exc:
            logger.error("ObjectiveRegistry: error al cargar: %s", exc)
            self._cache["obj:__all__"] = []

    def get(self, key: str, *args: Any) -> ObjectiveDefinition | None:
        self._ensure_loaded()
        return self._cache.get(self._cache_key("obj", key))

    def exists(self, key: str, *args: Any) -> bool:
        self._ensure_loaded()
        return self._cache_key("obj", key) in self._cache

    def list_available(self) -> list[str]:
        self._ensure_loaded()
        return list(self._cache.get("obj:__all__", []))

    def by_type(self, obj_type: ObjectiveType) -> list[ObjectiveDefinition]:
        self._ensure_loaded()
        return [
            obj for oid in self.list_available()
            if (obj := self.get(oid)) and obj.type == obj_type
        ]

    def by_priority(self, priority: Priority) -> list[ObjectiveDefinition]:
        self._ensure_loaded()
        return [
            obj for oid in self.list_available()
            if (obj := self.get(oid)) and obj.priority == priority
        ]

    def validate(self, item: Any) -> list[str]:
        errors: list[str] = []
        if not isinstance(item, ObjectiveDefinition):
            return ["Item no es ObjectiveDefinition."]
        if not item.id:
            errors.append("id es obligatorio.")
        if not item.name:
            errors.append("name es obligatorio.")
        if not item.description:
            errors.append("description es obligatoria.")
        if not item.reward:
            errors.append("reward es obligatorio.")
        return errors

    def warm_cache(self) -> dict[str, int]:
        self._ensure_loaded()
        ids = self.list_available()
        loaded = sum(1 for i in ids if self.get(i) is not None)
        return {"loaded": loaded, "errors": len(ids) - loaded}
