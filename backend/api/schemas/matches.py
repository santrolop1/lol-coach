"""Schemas Pydantic para la pantalla de Partidas y revisión de partida."""

from __future__ import annotations
from pydantic import BaseModel


class MatchCardSchema(BaseModel):
    is_win:        bool
    champion:      str
    role:          str
    kda:           str
    overall_score: float
    best_dim:      str
    worst_dim:     str
    match_id:      str


class MatchRowSchema(BaseModel):
    result:   str
    champion: str
    role:     str
    kda:      str
    cs:       int
    cs_pm:    float
    damage:   str
    duration: str
    date:     str


class MatchDetailRowSchema(BaseModel):
    date:       str
    champion:   str
    result:     str
    overall:    float
    kda:        str
    dimensions: dict[str, float]


class MatchesSummarySchema(BaseModel):
    total:   int
    wins:    int
    losses:  int
    winrate: float


class MatchesV2AnalysisSchema(BaseModel):
    role:        str
    detail_rows: list[MatchDetailRowSchema]
    avg_overall: float
    avg_dims:    dict[str, float]
    available:   bool


class PlayerSchema(BaseModel):
    riot_id: str
    tag:     str
    level:   int | None
    rank:    str | None
    tier:    str | None
    lp:      int | None


class MatchesResponse(BaseModel):
    has_config:       bool
    player:           PlayerSchema | None
    recent_cards:     list[MatchCardSchema]
    table_rows:       list[MatchRowSchema]
    summary:          MatchesSummarySchema
    v2_analysis:      MatchesV2AnalysisSchema | None
    available_roles:  list[str]
    available_champs: list[str]


# ── Match Review ───────────────────────────────────────────────────────────────

class MetricReviewSchema(BaseModel):
    key:              str
    label:            str
    value_str:        str
    avg_str:          str | None
    raw:              float | None
    raw_avg:          float | None
    direction:        str           # 'better' | 'worse' | 'neutral'
    higher_is_better: bool


class DimensionReviewSchema(BaseModel):
    name:       str
    name_es:    str
    score:      float | None
    avg_score:  float | None
    delta:      float | None
    is_best:    bool
    is_worst:   bool
    metrics:    list[MetricReviewSchema]
    notes:      list[str]
    context:    str


class MatchReviewResponse(BaseModel):
    found:            bool
    match_id:         str  = ""
    date:             str  = ""
    champion:         str  = ""
    role:             str  = ""
    is_win:           bool = False
    is_surrender:     bool = False
    duration:         str  = ""
    kda:              str  = ""
    kills:            int  = 0
    deaths_n:         int  = 0
    assists:          int  = 0
    cs:               int  = 0
    overall_score:    float | None = None
    avg_overall:      float | None = None
    overall_delta:    float | None = None
    dimensions:       list[DimensionReviewSchema] = []
    best_dim_name:    str | None = None
    worst_dim_name:   str | None = None
    key_error_title:  str | None = None
    key_error_body:   str | None = None
    focus_tip:        str | None = None
    sample_size:      int  = 0
    confidence:       str  = ""
    role_supported:   bool = True
