export interface DimensionScore {
  name:    string
  score:   number | null
  metrics: Record<string, number | null>
  notes:   string[]
}

export interface MatchScore {
  match_id:      string
  role:          string
  overall_score: number | null
  dimensions:    DimensionScore[]
  is_surrender:  boolean
  result:        string | null
  champion:      string | null
}

export interface ScoreResult {
  role:              string
  overall_score:     number | null
  trend:             string
  consistency_score: number | null
  confidence_level:  string
  match_scores:      MatchScore[]
  dimensions:        Record<string, number>
}

export interface WeeklyGoal {
  description: string
  metric:      string
  current:     number
  target:      number
  window:      string
}

export interface TrainingPlan {
  primary:   string
  secondary: string[]
}

export interface Strength {
  name:     string
  evidence: string
}

export interface CoachingResult {
  role:             string
  sample_size:      number
  confidence_level: string
  primary_problem:  string | null
  evidence:         string | null
  probable_cause:   string | null
  impact:           string | null
  trend_summary:    string | null
  session_warning:  string | null
  weekly_goal:      WeeklyGoal | null
  training_plan:    TrainingPlan | null
  strengths:        Strength[]
  improvements:     string[]
}

export interface Priority {
  title:          string
  metric_key:     string
  impact_score:   number
  confidence:     string
  evidence:       string
  recommendation: string
  current_value:  number | null
  target_value:   number | null
  unit:           string
}

export interface CoachingMetrics {
  cs_pm:       number | null
  dmg_pm:      number | null
  kp:          number | null
  kp_win:      number | null
  kp_loss:     number | null
  deaths:      number | null
  deaths_win:  number | null
  deaths_loss: number | null
  vision_pm:   number | null
  gold_pm:     number | null
  obj_pm:      number | null
  n:           number
  n_wins:      number
  n_losses:    number
}

export interface CoachingResponse {
  player_name:         string
  rank:                string
  lp:                  number
  last_match_date:     string | null
  role:                string
  sample_size:         number
  has_data:            boolean
  score_result:        ScoreResult | null
  coaching_result:     CoachingResult | null
  metrics:             CoachingMetrics | null
  priorities:          Priority[]
  available_champions: string[]
}
