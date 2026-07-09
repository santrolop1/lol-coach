// ── Lista de partidas ──────────────────────────────────────────────────────────

export interface MatchCard {
  is_win:        boolean
  champion:      string
  role:          string
  kda:           string
  overall_score: number
  best_dim:      string
  worst_dim:     string
  match_id:      string
}

export interface MatchSummary {
  total:   number
  wins:    number
  losses:  number
  winrate: number
}

export interface MatchesResponse {
  has_config:       boolean
  recent_cards:     MatchCard[]
  summary:          MatchSummary
  available_roles:  string[]
  available_champs: string[]
}

// ── Revisión de partida ────────────────────────────────────────────────────────

export type MetricDirection = 'better' | 'worse' | 'neutral'

export interface MetricReview {
  key:              string
  label:            string
  value_str:        string
  avg_str:          string | null
  raw:              number | null
  raw_avg:          number | null
  direction:        MetricDirection
  higher_is_better: boolean
}

export interface DimensionReview {
  name:       string
  name_es:    string
  score:      number | null
  avg_score:  number | null
  delta:      number | null
  is_best:    boolean
  is_worst:   boolean
  metrics:    MetricReview[]
  notes:      string[]
  context:    string
}

export interface MatchReviewResponse {
  found:            boolean
  match_id:         string
  date:             string
  champion:         string
  role:             string
  is_win:           boolean
  is_surrender:     boolean
  duration:         string
  kda:              string
  kills:            number
  deaths_n:         number
  assists:          number
  cs:               number
  overall_score:    number | null
  avg_overall:      number | null
  overall_delta:    number | null
  dimensions:       DimensionReview[]
  best_dim_name:    string | null
  worst_dim_name:   string | null
  key_error_title:  string | null
  key_error_body:   string | null
  focus_tip:        string | null
  sample_size:      number
  confidence:       string
  role_supported:   boolean
}
