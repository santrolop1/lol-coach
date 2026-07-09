"""Contrato base que todos los registries implementan."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any


class BaseRegistry(ABC):
    """
    Contrato universal de acceso al conocimiento.

    Los motores dependen de esta interfaz, nunca de implementaciones concretas.
    Ningún motor importa nada de knowledge/ directamente.
    """

    _cache: dict[str, Any]

    def __init__(self) -> None:
        self._cache = {}

    @abstractmethod
    def get(self, key: str, *args: Any) -> Any | None:
        """Carga un ítem por clave. Devuelve None si no existe."""

    @abstractmethod
    def exists(self, key: str, *args: Any) -> bool:
        """Comprueba si un ítem existe sin cargarlo completamente."""

    @abstractmethod
    def list_available(self) -> list[str]:
        """Devuelve todos los ítems disponibles (slugs)."""

    @abstractmethod
    def validate(self, item: Any) -> list[str]:
        """
        Valida un ítem.
        Devuelve lista de strings con errores encontrados.
        Lista vacía = ítem válido.
        """

    def warm_cache(self) -> dict[str, int]:
        """
        Carga todos los ítems en memoria.
        Devuelve dict con estadísticas: {"loaded": N, "errors": M}
        """
        loaded = 0
        errors = 0
        for key in self.list_available():
            item = self.get(key)
            if item is not None:
                loaded += 1
            else:
                errors += 1
        return {"loaded": loaded, "errors": errors}

    def invalidate_cache(self) -> None:
        """Limpia todo el cache. El próximo get() recargará desde la fuente."""
        self._cache.clear()

    def reload(self) -> dict[str, int]:
        """Invalida el cache y recarga todos los ítems."""
        self.invalidate_cache()
        return self.warm_cache()

    def _cache_key(self, *parts: str) -> str:
        return ":".join(parts)
