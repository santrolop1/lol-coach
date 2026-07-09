from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class SkillNode:
    key:         str
    name:        str
    description: str
    score:       float          # 0-100
    confidence:  float          # 0-1
    status:      str            # "locked" | "available" | "active" | "completed"
    priority:    int            # 1 = higher priority
    dim_key:     str            # scorer_v2 dimension name
    primary_metric: str


@dataclass
class ExerciseDot:
    """Un único juego evaluado contra el ejercicio activo."""
    match_id: str
    success:  bool
    value:    float | None      # valor real de la métrica en esa partida
    played_at: str


@dataclass
class Exercise:
    id:               str
    skill_key:        str
    skill_name:       str
    title:            str
    description:      str
    metric_key:       str
    threshold:        float
    direction:        str       # "less_than" | "greater_than"
    target_games:     int
    required_success: int
    success_count:    int
    games_checked:    int
    started_at:       str
    why:              str
    how_measured:     str
    expected_gain:    str
    unlocks:          str | None
    status:           str       # "active" | "completed" | "failed"
    dots:             list[ExerciseDot] = field(default_factory=list)


@dataclass
class DailyPlan:
    skill_name:        str
    exercise_title:    str
    focus_tip:         str      # una acción concreta para esta partida
    success_condition: str      # "Si terminas con ≤ X muertes"
    estimated_games:   int
    priority_label:    str      # "Alta" | "Media" | "Baja"


@dataclass
class WeeklySlot:
    week:       int             # 1-4
    skill_name: str
    skill_key:  str
    is_current: bool
    status:     str             # "completed" | "active" | "upcoming"
    goal_str:   str


@dataclass
class TrainingHistoryEntry:
    exercise_id:   str
    skill_key:     str
    skill_name:    str
    title:         str
    started_at:    str
    completed_at:  str | None
    games_checked: int
    success_count: int
    impact:        float        # mejora de score estimada conseguida


@dataclass
class TrainingViewModel:
    has_data:          bool
    role:              str               = ""
    total_matches:     int               = 0
    games_needed_msg:  str | None        = None
    skill_tree:        list[SkillNode]   = field(default_factory=list)
    active_exercise:   Exercise | None   = None
    daily_plan:        DailyPlan | None  = None
    weekly_roadmap:    list[WeeklySlot]  = field(default_factory=list)
    history:           list[TrainingHistoryEntry] = field(default_factory=list)
    next_skill_name:   str | None        = None
    next_skill_reason: str | None        = None
    confidence:        str               = "insufficient"
