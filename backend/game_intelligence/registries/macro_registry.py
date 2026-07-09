"""MacroRegistry — acceso al conocimiento de Macro Patterns y Win Conditions."""

from __future__ import annotations
import logging
from typing import Any

from .base import BaseRegistry
from ..models.macro import MacroPattern, WinCondition

logger = logging.getLogger(__name__)


class MacroRegistry(BaseRegistry):
    """
    Carga y sirve MacroPattern y WinCondition.
    Fuentes:
      knowledge/macro/patterns.py       → PATTERNS
      knowledge/macro/win_conditions.py → WIN_CONDITIONS
    """

    def _ensure_loaded(self) -> None:
        if "macro:__all__" in self._cache:
            return
        try:
            from ..knowledge.macro.patterns import PATTERNS
            from ..knowledge.macro.win_conditions import WIN_CONDITIONS
            for p in PATTERNS:
                self._cache[self._cache_key("macro", p.id)] = p
            for w in WIN_CONDITIONS:
                self._cache[self._cache_key("win", w.id)] = w
            self._cache["macro:__all__"] = [p.id for p in PATTERNS]
            self._cache["win:__all__"] = [w.id for w in WIN_CONDITIONS]
            logger.debug(
                "MacroRegistry: %d patrones, %d win conditions.",
                len(PATTERNS), len(WIN_CONDITIONS),
            )
        except Exception as exc:
            logger.error("MacroRegistry: error al cargar: %s", exc)
            self._cache.setdefault("macro:__all__", [])
            self._cache.setdefault("win:__all__", [])

    def get(self, key: str, *args: Any) -> MacroPattern | None:
        self._ensure_loaded()
        return self._cache.get(self._cache_key("macro", key))

    def get_win_condition(self, key: str) -> WinCondition | None:
        self._ensure_loaded()
        return self._cache.get(self._cache_key("win", key))

    def exists(self, key: str, *args: Any) -> bool:
        self._ensure_loaded()
        return self._cache_key("macro", key) in self._cache

    def list_available(self) -> list[str]:
        self._ensure_loaded()
        return list(self._cache.get("macro:__all__", []))

    def list_win_conditions(self) -> list[str]:
        self._ensure_loaded()
        return list(self._cache.get("win:__all__", []))

    def validate(self, item: Any) -> list[str]:
        errors: list[str] = []
        if isinstance(item, MacroPattern):
            if not item.id:
                errors.append("id es obligatorio.")
            if not item.name:
                errors.append("name es obligatorio.")
            if not item.description:
                errors.append("description es obligatoria.")
            if not item.when_to_apply:
                errors.append("when_to_apply es obligatorio.")
        elif isinstance(item, WinCondition):
            if not item.id:
                errors.append("id es obligatorio.")
            if not item.name:
                errors.append("name es obligatorio.")
            if not item.description:
                errors.append("description es obligatoria.")
        else:
            errors.append("Item no es MacroPattern ni WinCondition.")
        return errors

    def warm_cache(self) -> dict[str, int]:
        self._ensure_loaded()
        macro_ids = self.list_available()
        win_ids = self.list_win_conditions()
        loaded = sum(1 for i in macro_ids if self.get(i) is not None)
        loaded += sum(1 for i in win_ids if self.get_win_condition(i) is not None)
        total = len(macro_ids) + len(win_ids)
        return {"loaded": loaded, "errors": total - loaded}
