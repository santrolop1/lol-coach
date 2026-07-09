// Tipos compartidos por todas las features. Son la fuente de verdad del contrato con el backend.

export type Trend = 'improving' | 'stable' | 'declining'
export type ConfidenceLevel = 'reliable' | 'low_sample' | 'insufficient'
export type Role = 'ADC' | 'TOP'

// ── Health ─────────────────────────────────────────────────────────────────────

export interface HealthResponse {
  status:    'ok' | 'error'
  version:   string
  db:        'ok' | 'error'
  lcu:       'connected' | 'disconnected'
  riot_api:  'configured' | 'not_configured'
  last_sync: string | null
}

// ── Dashboard ──────────────────────────────────────────────────────────────────

export interface RoleSummary {
  has_data?:         boolean
  overall_score?:    number | null
  trend?:            Trend | null
  confidence_level?: ConfidenceLevel | string | null
  sample_size?:      number
  primary_problem?:  string | null
  top_priority?:     string | null
  winrate?:          number
}

export interface DashboardResponse {
  player_name:   string
  rank:          string | null
  lp:            number | null
  is_configured: boolean
  last_sync:     string | null
  sync_label:    string
  roles: Partial<Record<Role, RoleSummary>>
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

export interface SyncResponse {
  status:  string
  saved:   number
  skipped: number
  errors:  number
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

// ── Matches ────────────────────────────────────────────────────────────────────

export interface MatchCard {
  is_win:        boolean
  champion:      string
  role:          string
  kda:           string
  overall_score: number | null
  best_dim:      string | null
  worst_dim:     string | null
  match_id:      string
}
