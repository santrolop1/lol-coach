"""VisionRegistry — acceso al conocimiento de Visión."""

from __future__ import annotations
import logging
from typing import Any

from .base import BaseRegistry
from ..models.vision import WardSpot, VisionPattern, VisionPurpose, VisionZone

logger = logging.getLogger(__name__)


class VisionRegistry(BaseRegistry):
    """
    Carga y sirve WardSpot y VisionPattern.
    Fuentes:
      knowledge/vision/ward_spots.py → WARD_SPOTS
      knowledge/vision/patterns.py   → PATTERNS
    """

    def _ensure_loaded(self) -> None:
        if "vision:__all_spots__" in self._cache:
            return
        try:
            from ..knowledge.vision.ward_spots import WARD_SPOTS
            from ..knowledge.vision.patterns import PATTERNS
            for spot in WARD_SPOTS:
                self._cache[self._cache_key("spot", spot.id)] = spot
            for pattern in PATTERNS:
                self._cache[self._cache_key("vpattern", pattern.id)] = pattern
            self._cache["vision:__all_spots__"] = [s.id for s in WARD_SPOTS]
            self._cache["vision:__all_patterns__"] = [p.id for p in PATTERNS]
            logger.debug(
                "VisionRegistry: %d spots, %d patrones.",
                len(WARD_SPOTS), len(PATTERNS),
            )
        except Exception as exc:
            logger.error("VisionRegistry: error al cargar: %s", exc)
            self._cache.setdefault("vision:__all_spots__", [])
            self._cache.setdefault("vision:__all_patterns__", [])

    def get(self, key: str, *args: Any) -> WardSpot | None:
        """Devuelve un WardSpot por ID."""
        self._ensure_loaded()
        return self._cache.get(self._cache_key("spot", key))

    def get_pattern(self, pattern_id: str) -> VisionPattern | None:
        self._ensure_loaded()
        return self._cache.get(self._cache_key("vpattern", pattern_id))

    def exists(self, key: str, *args: Any) -> bool:
        self._ensure_loaded()
        return self._cache_key("spot", key) in self._cache

    def list_available(self) -> list[str]:
        self._ensure_loaded()
        return list(self._cache.get("vision:__all_spots__", []))

    def list_patterns(self) -> list[str]:
        self._ensure_loaded()
        return list(self._cache.get("vision:__all_patterns__", []))

    def spots_by_zone(self, zone: VisionZone) -> list[WardSpot]:
        self._ensure_loaded()
        return [
            spot for sid in self.list_available()
            if (spot := self.get(sid)) and spot.zone == zone
        ]

    def spots_by_purpose(self, purpose: VisionPurpose) -> list[WardSpot]:
        self._ensure_loaded()
        return [
            spot for sid in self.list_available()
            if (spot := self.get(sid)) and spot.purpose == purpose
        ]

    def validate(self, item: Any) -> list[str]:
        errors: list[str] = []
        if isinstance(item, WardSpot):
            if not item.id:
                errors.append("id es obligatorio.")
            if not item.description:
                errors.append("description es obligatoria.")
            if not item.when_to_use:
                errors.append("when_to_use es obligatorio.")
        elif isinstance(item, VisionPattern):
            if not item.id:
                errors.append("id es obligatorio.")
            if not item.description:
                errors.append("description es obligatoria.")
        else:
            errors.append("Item no es WardSpot ni VisionPattern.")
        return errors

    def warm_cache(self) -> dict[str, int]:
        self._ensure_loaded()
        spot_ids = self.list_available()
        pat_ids = self.list_patterns()
        loaded = sum(1 for i in spot_ids if self.get(i) is not None)
        loaded += sum(1 for i in pat_ids if self.get_pattern(i) is not None)
        total = len(spot_ids) + len(pat_ids)
        return {"loaded": loaded, "errors": total - loaded}
