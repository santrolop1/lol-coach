export type TrendDirection = 'improving' | 'declining' | 'stable'
export type Confidence    = 'high' | 'medium' | 'low' | 'reliable' | 'preliminary' | 'insufficient'
export type GoalStatus    = 'completed' | 'on_track' | 'at_risk' | 'not_started'
export type TrendArrow    = 'up' | 'down' | 'flat' | ''

export interface TimelinePoint {
  label:             string
  games_ago_start:   number
  games_ago_end:     number
  avg_score:         number | null
  dominant_champion: string | null
  sample_size:       number
  trend_arrow:       TrendArrow
}

export interface TrendInsight {
  category:   TrendDirection
  dim_name:   string
  label:      string
  delta:      number
  delta_pct:  number
  confidence: string
  champion:   string | null
}

export interface WeeklyGoal {
  title:          string
  metric_key:     string
  metric_label:   string
  target_value:   number
  target_str:     string
  current_avg:    number
  baseline:       number
  progress_count: number
  total_count:    number
  pct:            number
  status:         GoalStatus
  motivation:     string
}

export interface Habit {
  type:        'positive' | 'negative'
  title:       string
  description: string
  streak:      number
  is_active:   boolean
}

export interface ChampionInsight {
  champion:   string
  games:      number
  avg_score:  number
  vs_overall: number
  role:       string
}

export interface Recommendation {
  rank:       number
  title:      string
  body:       string
  evidence:   string
  impact:     'high' | 'medium'
  metric_key: string | null
}

export interface ProgressResponse {
  has_data:    boolean
  role:        string
  total_matches: number

  overall_trend:       TrendDirection
  overall_trend_label: string
  overall_delta:       number | null
  avg_recent:          number | null
  confidence:          string

  timeline:     TimelinePoint[]
  score_series: number[]

  improving: TrendInsight[]
  declining: TrendInsight[]
  stable:    TrendInsight[]

  habits:      Habit[]
  weekly_goal: WeeklyGoal | null

  champion_insights: ChampionInsight[]
  recommendations:   Recommendation[]

  min_games_needed: number
  games_needed_msg: string | null
}
