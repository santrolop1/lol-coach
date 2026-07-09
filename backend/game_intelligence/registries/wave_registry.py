"""WaveRegistry — acceso al conocimiento de Wave Management."""

from __future__ import annotations
import logging
from typing import Any

from .base import BaseRegistry
from ..models.wave import WaveStrategy

logger = logging.getLogger(__name__)
_NOT_LOADED = object()


class WaveRegistry(BaseRegistry):
    """
    Carga y sirve las WaveStrategy universales.
    Fuente: knowledge/wave/strategies.py → STRATEGIES: list[WaveStrategy]
    """

    def _ensure_loaded(self) -> None:
        if "wave:__all__" in self._cache:
            return
        try:
            from ..knowledge.wave.strategies import STRATEGIES
            for s in STRATEGIES:
                key = self._cache_key("wave", s.id)
                self._cache[key] = s
            self._cache["wave:__all__"] = [s.id for s in STRATEGIES]
            logger.debug("WaveRegistry: %d estrategias cargadas.", len(STRATEGIES))
        except Exception as exc:
            logger.error("WaveRegistry: error cargando estrategias: %s", exc)
            self._cache["wave:__all__"] = []

    def get(self, key: str, *args: Any) -> WaveStrategy | None:
        self._ensure_loaded()
        return self._cache.get(self._cache_key("wave", key))

    def exists(self, key: str, *args: Any) -> bool:
        self._ensure_loaded()
        return self._cache_key("wave", key) in self._cache

    def list_available(self) -> list[str]:
        self._ensure_loaded()
        return list(self._cache.get("wave:__all__", []))

    def validate(self, item: Any) -> list[str]:
        errors: list[str] = []
        if not isinstance(item, WaveStrategy):
            return ["Item no es una WaveStrategy."]
        if not item.id:
            errors.append("id es obligatorio.")
        if not item.name:
            errors.append("name es obligatorio.")
        if not item.technique:
            errors.append("technique es obligatorio.")
        if not item.description:
            errors.append("description es obligatoria.")
        if not item.when_to_use:
            errors.append("when_to_use es obligatorio.")
        if not item.why:
            errors.append("why es obligatorio.")
        return errors

    def warm_cache(self) -> dict[str, int]:
        self._ensure_loaded()
        ids = self.list_available()
        loaded = sum(1 for i in ids if self.get(i) is not None)
        errors = len(ids) - loaded
        return {"loaded": loaded, "errors": errors}
