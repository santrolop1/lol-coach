"""Schemas Pydantic para el Knowledge Engine."""

from __future__ import annotations
from pydantic import BaseModel


class GoalSchema(BaseModel):
    id:               str
    metric_key:       str
    metric_label:     str
    target_value:     float
    target_str:       str
    higher_is_better: bool
    check_window:     int
    status:           str
    created_at:       str
    completed_at:     str | None
    progress_count:   int
    total_count:      int
    pct:              float


class PatternSchema(BaseModel):
    id:          str
    category:    str
    title:       str
    description: str
    evidence:    str
    confidence:  float
    actionable:  str


class InsightSchema(BaseModel):
    rank:       int
    text:       str
    evidence:   str
    category:   str
    confidence: float


class RecommendationSchema(BaseModel):
    rank:        int
    title:       str
    body:        str
    why:         str
    impact:      str
    impact_pct:  int
    confidence:  float
    difficulty:  str
    goal_str:    str
    metric_key:  str | None


class SessionMatchSchema(BaseModel):
    match_id:      str
    champion:      str
    role:          str
    is_win:        bool
    kda:           str
    overall_score: float | None
    best_dim:      str | None
    worst_dim:     str | None


class SessionSummarySchema(BaseModel):
    has_session:   bool
    total_games:   int   = 0
    wins:          int   = 0
    losses:        int   = 0
    avg_score:     float | None = None
    best_aspect:   str | None   = None
    worst_aspect:  str | None   = None
    goal_progress: str | None   = None
    tip:           str | None   = None
    session_label: str          = ""
    matches:       list[SessionMatchSchema] = []


class MemoryEntrySchema(BaseModel):
    goal_title:   str
    status:       str
    created_at:   str
    completed_at: str | None
    metric_key:   str


class KnowledgeResponse(BaseModel):
    has_data:       bool
    role:           str  = ""
    total_matches:  int  = 0
    session:        SessionSummarySchema      = SessionSummarySchema(has_session=False)
    active_goal:    GoalSchema | None         = None
    memory:         list[MemoryEntrySchema]   = []
    patterns:       list[PatternSchema]       = []
    insights:       list[InsightSchema]       = []
    recommendations: list[RecommendationSchema] = []
    confidence:      str = "insufficient"
    games_needed_msg: str | None = None
