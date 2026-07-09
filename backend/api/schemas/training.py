from __future__ import annotations
from pydantic import BaseModel


class ExerciseDotSchema(BaseModel):
    match_id:  str
    success:   bool
    value:     float | None
    played_at: str


class ExerciseSchema(BaseModel):
    id:               str
    skill_key:        str
    skill_name:       str
    title:            str
    description:      str
    metric_key:       str
    threshold:        float
    direction:        str
    target_games:     int
    required_success: int
    success_count:    int
    games_checked:    int
    started_at:       str
    why:              str
    how_measured:     str
    expected_gain:    str
    unlocks:          str | None
    status:           str
    dots:             list[ExerciseDotSchema] = []


class SkillNodeSchema(BaseModel):
    key:            str
    name:           str
    description:    str
    score:          float
    confidence:     float
    status:         str
    priority:       int
    dim_key:        str
    primary_metric: str


class DailyPlanSchema(BaseModel):
    skill_name:        str
    exercise_title:    str
    focus_tip:         str
    success_condition: str
    estimated_games:   int
    priority_label:    str


class WeeklySlotSchema(BaseModel):
    week:       int
    skill_name: str
    skill_key:  str
    is_current: bool
    status:     str
    goal_str:   str


class TrainingHistoryEntrySchema(BaseModel):
    exercise_id:   str
    skill_key:     str
    skill_name:    str
    title:         str
    started_at:    str
    completed_at:  str | None
    games_checked: int
    success_count: int
    impact:        float


class TrainingResponse(BaseModel):
    has_data:          bool
    role:              str                          = ""
    total_matches:     int                          = 0
    games_needed_msg:  str | None                   = None
    skill_tree:        list[SkillNodeSchema]        = []
    active_exercise:   ExerciseSchema | None        = None
    daily_plan:        DailyPlanSchema | None       = None
    weekly_roadmap:    list[WeeklySlotSchema]       = []
    history:           list[TrainingHistoryEntrySchema] = []
    next_skill_name:   str | None                   = None
    next_skill_reason: str | None                   = None
    confidence:        str                          = "insufficient"
