"""
server/schemas.py — Validación de entrada (Pydantic v2).

Toda petición se valida ANTES de tocar la base de datos:
  - extra="forbid": cualquier campo no previsto → 422. Si un cliente
    defectuoso intentara enviar un puuid o api_key, el servidor lo rechaza.
  - Enums cerrados para rol / resultado / tier / clasificación.
  - Rangos numéricos acotados (scores 0-100, duración 3-120 min, KP 0-1…).
  - Lotes limitados a 100 elementos.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Role   = Literal["ADC", "TOP", "MID", "JGL", "SUP"]
Result = Literal["WIN", "LOSS"]
Tier   = Literal[
    "UNRANKED", "IRON", "BRONZE", "SILVER", "GOLD", "PLATINUM",
    "EMERALD", "DIAMOND", "MASTER", "GRANDMASTER", "CHALLENGER",
]
Classification = Literal["MAIN", "CARRY", "COMFORT", "TRAP", "SOLID"]
Confidence     = Literal["insufficient", "preliminary", "reliable", "robust"]
Trend          = Literal["improving", "stable", "declining"]

_CHAMP = Field(min_length=2, max_length=32, pattern=r"^[A-Za-z][A-Za-z0-9]*$")


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MatchStats(_Strict):
    kills:              Optional[int]   = Field(None, ge=0, le=100)
    deaths:             Optional[int]   = Field(None, ge=0, le=100)
    assists:            Optional[int]   = Field(None, ge=0, le=150)
    cs_per_min:         Optional[float] = Field(None, ge=0, le=20)
    gold_per_min:       Optional[float] = Field(None, ge=0, le=2000)
    damage_per_min:     Optional[float] = Field(None, ge=0, le=10000)
    kill_participation: Optional[float] = Field(None, ge=0, le=1)
    team_damage_pct:    Optional[float] = Field(None, ge=0, le=1)
    cs_at_10:           Optional[int]   = Field(None, ge=0, le=150)
    vision_score:       Optional[int]   = Field(None, ge=0, le=300)


class MatchSummaryIn(_Strict):
    schema_version: int            = Field(ge=1, le=10)
    client_version: str            = Field(min_length=1, max_length=32)
    install_id:     str            = Field(min_length=8, max_length=64, pattern=r"^[a-f0-9]+$")
    match_hash:     str            = Field(min_length=8, max_length=32, pattern=r"^[a-f0-9]+$")
    patch:          Optional[str]  = Field(None, max_length=16, pattern=r"^\d{1,3}\.\d{1,3}$")
    role:           Role
    champion:       str            = _CHAMP
    elo_tier:       Tier
    result:         Result
    duration_sec:   int            = Field(ge=180, le=7200)   # 3 min (remake) – 2 h
    surrender:      bool           = False
    overall_score:  Optional[float] = Field(None, ge=0, le=100)
    dimensions:     dict[str, float] = Field(default_factory=dict, max_length=6)
    stats:          MatchStats     = Field(default_factory=MatchStats)
    loadout:        Optional[dict] = None   # reservado: build/runas/hechizos


class CoachingSnapshotIn(_Strict):
    schema_version:   int           = Field(ge=1, le=10)
    client_version:   str           = Field(min_length=1, max_length=32)
    install_id:       str           = Field(min_length=8, max_length=64, pattern=r"^[a-f0-9]+$")
    role:             Role
    elo_tier:         Tier
    confidence_level: Confidence
    sample_size:      int           = Field(ge=0, le=1000)
    primary_problem:  str           = Field(min_length=1, max_length=128)
    improvements:     list[str]     = Field(default_factory=list, max_length=5)
    strengths:        list[str]     = Field(default_factory=list, max_length=5)
    overall_score:    Optional[float] = Field(None, ge=0, le=100)
    consistency:      Optional[float] = Field(None, ge=0, le=100)
    trend:            Trend


class ChampionReportIn(_Strict):
    schema_version: int   = Field(ge=1, le=10)
    client_version: str   = Field(min_length=1, max_length=32)
    install_id:     str   = Field(min_length=8, max_length=64, pattern=r"^[a-f0-9]+$")
    role:           Role
    elo_tier:       Tier
    champion:       str   = _CHAMP
    games:          int   = Field(ge=1, le=10000)
    wins:           int   = Field(ge=0, le=10000)
    avg_score:      float = Field(ge=0, le=100)
    classification: Classification


class MatchBatch(_Strict):
    items: list[MatchSummaryIn] = Field(min_length=1, max_length=100)


class SessionBatch(_Strict):
    items: list[CoachingSnapshotIn] = Field(min_length=1, max_length=100)


class ChampionBatch(_Strict):
    items: list[ChampionReportIn] = Field(min_length=1, max_length=100)


class IngestResult(_Strict):
    accepted:   int
    duplicates: int


class KnowledgeVersionOut(_Strict):
    version:    int
    created_at: str


class KnowledgeOut(_Strict):
    version:    int
    created_at: str
    payload:    dict
