// ── Health ─────────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status:    'ok' | 'error'
  version:   string
  db:        'ok' | 'error'
  lcu:       'connected' | 'disconnected'
  riot_api:  'configured' | 'not_configured'
  last_sync: string | null
}

// ── Settings ───────────────────────────────────────────────────────────────────

export interface SettingsResponse {
  is_configured: boolean
  puuid:         string | null
  api_key:       string | null
  platform:      string | null
  platform_name: string | null
  riot_id:       string | null
  tag:           string | null
  level:         number | null
  rank:          string | null
  tier:          string | null
  lp:            number | null
}

// ── Dashboard ──────────────────────────────────────────────────────────────────

export interface RoleSummary {
  has_data?:        boolean
  overall_score?:   number
  trend?:           string
  confidence_level?: string
  sample_size?:     number
  primary_problem?: string | null
  top_priority?:    string | null
  winrate?:         number
}

export interface DashboardResponse {
  player_name:   string
  rank:          string | null
  lp:            number | null
  is_configured: boolean
  last_sync:     string | null
  sync_label:    string
  roles: {
    ADC?: RoleSummary
    TOP?: RoleSummary
  }
}

// ── Coaching ───────────────────────────────────────────────────────────────────

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

export interface WeeklyGoal {
  description: string
  metric:      string
  current:     number
  target:      number
  window:      number
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

export interface ScoreResult {
  role:              string
  overall_score:     number | null
  trend:             string
  consistency_score: number | null
  confidence_level:  string
  dimensions:        Record<string, number>
  match_scores:      unknown[]
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

// ── Matches ────────────────────────────────────────────────────────────────────

export interface MatchCard {
  is_win:      boolean
  champion:    string
  role:        string
  kda:         string
  overall_score: number | null
  best_dim:    string | null
  worst_dim:   string | null
  match_id:    string
}

export interface MatchRow {
  result:   string
  champion: string
  role:     string
  kda:      string
  cs:       number
  cs_pm:    number
  damage:   string
  duration: string
  date:     string
}

export interface MatchesSummary {
  total:   number
  wins:    number
  losses:  number
  winrate: number
}

export interface MatchesResponse {
  has_config:       boolean
  player:           Record<string, unknown> | null
  recent_cards:     MatchCard[]
  table_rows:       MatchRow[]
  summary:          MatchesSummary
  v2_analysis:      unknown | null
  available_roles:  string[]
  available_champs: string[]
}

// ── Draft ──────────────────────────────────────────────────────────────────────

export interface DraftResponse {
  lcu_connected:  boolean
  phase:          string | null
  phase_label:    string
  role:           string | null
  role_supported: boolean
  session:        Record<string, unknown> | null
  advice:         Record<string, unknown> | null
  champion_pool:  Record<string, unknown> | null
}
