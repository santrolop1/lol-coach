"""Schemas Pydantic para la pantalla de Draft."""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel


class DraftResponse(BaseModel):
    lcu_connected:  bool
    phase:          str | None
    phase_label:    str
    role:           str | None
    role_supported: bool
    session:        dict[str, Any] | None
    advice:         dict[str, Any] | None
    champion_pool:  dict[str, Any] | None
