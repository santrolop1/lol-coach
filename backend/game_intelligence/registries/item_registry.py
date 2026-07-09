"""ItemRegistry — acceso al conocimiento de Items y Builds."""

from __future__ import annotations
import logging
from typing import Any

from .base import BaseRegistry
from ..models.item import ItemDefinition, ItemBuild

logger = logging.getLogger(__name__)


class ItemRegistry(BaseRegistry):
    """
    Carga y sirve ItemDefinition e ItemBuild.
    Fuentes:
      knowledge/items/definitions.py → ITEMS
      knowledge/items/builds.py      → BUILDS
    """

    def _ensure_loaded(self) -> None:
        if "item:__all__" in self._cache:
            return
        try:
            from ..knowledge.items.definitions import ITEMS
            from ..knowledge.items.builds import BUILDS
            for item in ITEMS:
                self._cache[self._cache_key("item", item.id)] = item
            for build in BUILDS:
                self._cache[self._cache_key("build", build.id)] = build
            self._cache["item:__all__"] = [i.id for i in ITEMS]
            self._cache["build:__all__"] = [b.id for b in BUILDS]
            logger.debug("ItemRegistry: %d items, %d builds.", len(ITEMS), len(BUILDS))
        except Exception as exc:
            logger.error("ItemRegistry: error al cargar: %s", exc)
            self._cache.setdefault("item:__all__", [])
            self._cache.setdefault("build:__all__", [])

    def get(self, key: str, *args: Any) -> ItemDefinition | None:
        self._ensure_loaded()
        return self._cache.get(self._cache_key("item", key))

    def get_build(self, build_id: str) -> ItemBuild | None:
        self._ensure_loaded()
        return self._cache.get(self._cache_key("build", build_id))

    def exists(self, key: str, *args: Any) -> bool:
        self._ensure_loaded()
        return self._cache_key("item", key) in self._cache

    def list_available(self) -> list[str]:
        self._ensure_loaded()
        return list(self._cache.get("item:__all__", []))

    def list_builds(self) -> list[str]:
        self._ensure_loaded()
        return list(self._cache.get("build:__all__", []))

    def validate(self, item: Any) -> list[str]:
        errors: list[str] = []
        if isinstance(item, ItemDefinition):
            if not item.id:
                errors.append("id es obligatorio.")
            if not item.name:
                errors.append("name es obligatorio.")
            if not item.when_to_buy:
                errors.append("when_to_buy es obligatorio.")
            if item.cost <= 0:
                errors.append("cost debe ser positivo.")
        elif isinstance(item, ItemBuild):
            if not item.id:
                errors.append("id es obligatorio.")
            if not item.name:
                errors.append("name es obligatorio.")
            if not item.core:
                errors.append("core no puede estar vacío.")
        else:
            errors.append("Item no es ItemDefinition ni ItemBuild.")
        return errors

    def warm_cache(self) -> dict[str, int]:
        self._ensure_loaded()
        item_ids = self.list_available()
        build_ids = self.list_builds()
        loaded = sum(1 for i in item_ids if self.get(i) is not None)
        loaded += sum(1 for b in build_ids if self.get_build(b) is not None)
        total = len(item_ids) + len(build_ids)
        return {"loaded": loaded, "errors": total - loaded}
