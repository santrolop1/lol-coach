"""Schemas Pydantic para el Coaching Progresivo."""

from __future__ import annotations
from pydantic import BaseModel


class TimelinePointSchema(BaseModel):
    label:             str
    games_ago_start:   int
    games_ago_end:     int
    avg_score:         float | None
    dominant_champion: str | None
    sample_size:       int
    trend_arrow:       str   # "up" | "down" | "flat" | ""


class TrendInsightSchema(BaseModel):
    category:   str           # "improving" | "declining" | "stable"
    dim_name:   str
    label:      str
    delta:      float
    delta_pct:  float
    confidence: str           # "high" | "medium" | "low"
    champion:   str | None


class WeeklyGoalSchema(BaseModel):
    title:          str
    metric_key:     str
    metric_label:   str
    target_value:   float
    target_str:     str
    current_avg:    float
    baseline:       float
    progress_count: int
    total_count:    int
    pct:            float
    status:         str   # "completed" | "on_track" | "at_risk" | "not_started"
    motivation:     str


class HabitSchema(BaseModel):
    type:        str   # "positive" | "negative"
    title:       str
    description: str
    streak:      int
    is_active:   bool


class ChampionInsightSchema(BaseModel):
    champion:   str
    games:      int
    avg_score:  float
    vs_overall: float
    role:       str


class RecommendationSchema(BaseModel):
    rank:       int
    title:      str
    body:       str
    evidence:   str
    impact:     str   # "high" | "medium"
    metric_key: str | None


class ProgressResponse(BaseModel):
    has_data:    bool
    role:        str  = ""
    total_matches: int = 0

    # Hero
    overall_trend:       str         = "stable"
    overall_trend_label: str         = "Estable"
    overall_delta:       float | None = None
    avg_recent:          float | None = None
    confidence:          str         = "insufficient"

    # Timeline
    timeline:     list[TimelinePointSchema]   = []
    score_series: list[float]                 = []

    # Insights
    improving: list[TrendInsightSchema] = []
    declining: list[TrendInsightSchema] = []
    stable:    list[TrendInsightSchema] = []

    # Hábitos
    habits: list[HabitSchema] = []

    # Objetivo semanal
    weekly_goal: WeeklyGoalSchema | None = None

    # Análisis por campeón
    champion_insights: list[ChampionInsightSchema] = []

    # Recomendaciones
    recommendations: list[RecommendationSchema] = []

    # Meta
    min_games_needed: int      = 10
    games_needed_msg: str | None = None
