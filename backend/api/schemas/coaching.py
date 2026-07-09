"""Schemas Pydantic para la pantalla de Coaching."""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel


class CoachingMetricsSchema(BaseModel):
    cs_pm:       float | None
    dmg_pm:      float | None
    kp:          float | None
    kp_win:      float | None
    kp_loss:     float | None
    deaths:      float | None
    deaths_win:  float | None
    deaths_loss: float | None
    vision_pm:   float | None
    gold_pm:     float | None
    obj_pm:      float | None
    n:           int
    n_wins:      int
    n_losses:    int


class PrioritySchema(BaseModel):
    title:         str
    metric_key:    str
    impact_score:  int
    confidence:    str
    evidence:      str
    recommendation: str
    current_value: float | None
    target_value:  float | None
    unit:          str


class WeeklyGoalSchema(BaseModel):
    description: str
    metric:      str
    current:     float
    target:      float
    window:      str


class TrainingPlanSchema(BaseModel):
    primary:   str
    secondary: list[str]


class StrengthSchema(BaseModel):
    name:     str
    evidence: str


class CoachingResultSchema(BaseModel):
    role:             str
    sample_size:      int
    confidence_level: str
    primary_problem:  str | None
    evidence:         str | None = None
    probable_cause:   str | None = None
    impact:           str | None = None
    trend_summary:    str | None = None
    session_warning:  str | None
    weekly_goal:      WeeklyGoalSchema | None
    training_plan:    TrainingPlanSchema | None
    strengths:        list[StrengthSchema]
    improvements:     list[str] = []


class DimensionScoreSchema(BaseModel):
    name:    str
    score:   float | None
    metrics: dict[str, Any]
    notes:   list[str]


class MatchScoreSchema(BaseModel):
    match_id:      str
    role:          str
    overall_score: float | None
    dimensions:    list[DimensionScoreSchema]
    is_surrender:  bool
    result:        str | None
    champion:      str | None


class ScoreResultSchema(BaseModel):
    role:              str
    overall_score:     float | None
    trend:             str
    consistency_score: float | None
    confidence_level:  str
    match_scores:      list[MatchScoreSchema]
    dimensions:        dict[str, float]


class CoachingResponse(BaseModel):
    player_name:     str
    rank:            str
    lp:              int
    last_match_date: str | None
    role:            str
    sample_size:     int
    has_data:        bool
    score_result:    ScoreResultSchema | None
    coaching_result: CoachingResultSchema | None
    metrics:         CoachingMetricsSchema | None
    priorities:      list[PrioritySchema]
    available_champions: list[str]
