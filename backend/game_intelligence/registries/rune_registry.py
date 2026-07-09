"""RuneRegistry — acceso al conocimiento de Runas."""

from __future__ import annotations
import logging
from typing import Any

from .base import BaseRegistry
from ..models.rune import RuneTree, RunePage

logger = logging.getLogger(__name__)


class RuneRegistry(BaseRegistry):
    """
    Carga y sirve RuneTree y RunePage.
    Fuentes:
      knowledge/runes/trees.py → TREES
      knowledge/runes/pages.py → PAGES
    """

    def _ensure_loaded(self) -> None:
        if "rune:__all_pages__" in self._cache:
            return
        try:
            from ..knowledge.runes.trees import TREES
            from ..knowledge.runes.pages import PAGES
            for t in TREES:
                self._cache[self._cache_key("tree", t.id)] = t
            for p in PAGES:
                self._cache[self._cache_key("page", p.id)] = p
            self._cache["rune:__all_trees__"] = [t.id for t in TREES]
            self._cache["rune:__all_pages__"] = [p.id for p in PAGES]
            logger.debug("RuneRegistry: %d árboles, %d páginas.", len(TREES), len(PAGES))
        except Exception as exc:
            logger.error("RuneRegistry: error al cargar: %s", exc)
            self._cache.setdefault("rune:__all_trees__", [])
            self._cache.setdefault("rune:__all_pages__", [])

    def get(self, key: str, *args: Any) -> RunePage | None:
        """Busca una RunePage por ID."""
        self._ensure_loaded()
        return self._cache.get(self._cache_key("page", key))

    def get_tree(self, tree_id: str) -> RuneTree | None:
        self._ensure_loaded()
        return self._cache.get(self._cache_key("tree", tree_id))

    def exists(self, key: str, *args: Any) -> bool:
        self._ensure_loaded()
        return self._cache_key("page", key) in self._cache

    def list_available(self) -> list[str]:
        self._ensure_loaded()
        return list(self._cache.get("rune:__all_pages__", []))

    def list_trees(self) -> list[str]:
        self._ensure_loaded()
        return list(self._cache.get("rune:__all_trees__", []))

    def pages_by_keystone(self, keystone: str) -> list[RunePage]:
        self._ensure_loaded()
        return [
            p for pid in self.list_available()
            if (p := self.get(pid)) and p.primary_keystone == keystone
        ]

    def validate(self, item: Any) -> list[str]:
        errors: list[str] = []
        if isinstance(item, RunePage):
            if not item.id:
                errors.append("id es obligatorio.")
            if not item.primary_keystone:
                errors.append("primary_keystone es obligatorio.")
            if not item.primary_tree:
                errors.append("primary_tree es obligatorio.")
            if not item.when_to_use:
                errors.append("when_to_use es obligatorio.")
        elif isinstance(item, RuneTree):
            if not item.id:
                errors.append("id es obligatorio.")
            if not item.name:
                errors.append("name es obligatorio.")
        else:
            errors.append("Item no es RunePage ni RuneTree.")
        return errors

    def warm_cache(self) -> dict[str, int]:
        self._ensure_loaded()
        page_ids = self.list_available()
        tree_ids = self.list_trees()
        loaded = sum(1 for i in page_ids if self.get(i) is not None)
        loaded += sum(1 for i in tree_ids if self.get_tree(i) is not None)
        total = len(page_ids) + len(tree_ids)
        return {"loaded": loaded, "errors": total - loaded}
