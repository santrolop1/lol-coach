"""
OverlayConfig — configuración persistente del overlay.

Persistencia en tabla config de SQLite con clave "live_coach_overlay_config_v1".
Si la clave no existe, devuelve la configuración por defecto.
"""

from __future__ import annotations
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Any

logger = logging.getLogger(__name__)

_CONFIG_KEY = "live_coach_overlay_config_v1"


@dataclass
class OverlayConfig:
    """Configuración completa del overlay. Serializable a JSON."""

    # Posición y tamaño (px relativos a la pantalla principal)
    x: int = 20
    y: int = 20
    width: int = 280
    height: int = 420

    # Apariencia
    opacity: float = 0.90           # 0.0 – 1.0
    scale: float = 1.0              # multiplicador de fuente/padding
    compact_mode: bool = False
    always_on_top: bool = True

    # Monitor (índice 0-based; -1 = seguir ventana principal)
    monitor_index: int = 0

    # Widgets habilitados
    widgets_enabled: dict[str, bool] = field(default_factory=lambda: {
        "champion":           True,
        "current_objective":  True,
        "power_spike":        True,
        "build":              True,
        "training":           True,
        "notifications":      True,
        "status":             True,
        "wave_tip":           False,   # deshabilitado por defecto (info avanzada)
        "macro_tip":          False,
    })

    # Frecuencia de consejos (segundos entre tips opcionales)
    tip_interval_seconds: int = 30

    # Nivel de detalle: "minimal" | "normal" | "detailed"
    detail_level: str = "normal"

    # Auto-ocultar cuando no hay partida activa
    auto_hide_on_idle: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OverlayConfig":
        valid_fields = {f for f in cls.__dataclass_fields__}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)

    def is_widget_enabled(self, widget_id: str) -> bool:
        return self.widgets_enabled.get(widget_id, True)


def load_config(db_module=None) -> OverlayConfig:
    """
    Carga la configuración desde SQLite.
    Si no existe o falla, devuelve la configuración por defecto.
    """
    if db_module is None:
        try:
            import db as db_module
        except ImportError:
            return OverlayConfig()

    try:
        raw = db_module.get_config(_CONFIG_KEY)
        if raw is None:
            return OverlayConfig()
        data = json.loads(raw) if isinstance(raw, str) else raw
        return OverlayConfig.from_dict(data)
    except Exception as exc:
        logger.warning("Error cargando OverlayConfig: %s — usando defaults", exc)
        return OverlayConfig()


def save_config(config: OverlayConfig, db_module=None) -> None:
    """Persiste la configuración en SQLite."""
    if db_module is None:
        try:
            import db as db_module
        except ImportError:
            logger.warning("db module no disponible — config no persistida")
            return
    try:
        db_module.save_config(_CONFIG_KEY, json.dumps(config.to_dict()))
    except Exception as exc:
        logger.error("Error guardando OverlayConfig: %s", exc)
