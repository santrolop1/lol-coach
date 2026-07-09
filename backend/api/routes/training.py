from __future__ import annotations
import dataclasses

from fastapi import APIRouter
from backend.training.engine import build_training
from backend.api.schemas.training import TrainingResponse

router = APIRouter()


def _dc(obj):
    """Convierte dataclasses anidados a dict recursivamente."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _dc(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, list):
        return [_dc(i) for i in obj]
    return obj


@router.get("/training", response_model=TrainingResponse)
def get_training():
    vm = build_training()
    return TrainingResponse(**_dc(vm))
