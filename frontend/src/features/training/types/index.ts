export interface ExerciseDot {
  match_id:  string
  success:   boolean
  value:     number | null
  played_at: string
}

export interface Exercise {
  id:               string
  skill_key:        string
  skill_name:       string
  title:            string
  description:      string
  metric_key:       string
  threshold:        number
  direction:        'less_than' | 'greater_than'
  target_games:     number
  required_success: number
  success_count:    number
  games_checked:    number
  started_at:       string
  why:              string
  how_measured:     string
  expected_gain:    string
  unlocks:          string | null
  status:           'active' | 'completed' | 'failed'
  dots:             ExerciseDot[]
}

export interface SkillNode {
  key:            string
  name:           string
  description:    string
  score:          number
  confidence:     number
  status:         'locked' | 'available' | 'active' | 'completed'
  priority:       number
  dim_key:        string
  primary_metric: string
}

export interface DailyPlan {
  skill_name:        string
  exercise_title:    string
  focus_tip:         string
  success_condition: string
  estimated_games:   number
  priority_label:    string
}

export interface WeeklySlot {
  week:       number
  skill_name: string
  skill_key:  string
  is_current: boolean
  status:     'completed' | 'active' | 'upcoming'
  goal_str:   string
}

export interface TrainingHistoryEntry {
  exercise_id:   string
  skill_key:     string
  skill_name:    string
  title:         string
  started_at:    string
  completed_at:  string | null
  games_checked: number
  success_count: number
  impact:        number
}

export interface TrainingResponse {
  has_data:          boolean
  role:              string
  total_matches:     number
  games_needed_msg:  string | null
  skill_tree:        SkillNode[]
  active_exercise:   Exercise | null
  daily_plan:        DailyPlan | null
  weekly_roadmap:    WeeklySlot[]
  history:           TrainingHistoryEntry[]
  next_skill_name:   string | null
  next_skill_reason: string | null
  confidence:        string
}
