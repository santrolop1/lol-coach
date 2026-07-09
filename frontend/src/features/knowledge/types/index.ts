export interface Goal {
  id:               string
  metric_key:       string
  metric_label:     string
  target_value:     number
  target_str:       string
  higher_is_better: boolean
  check_window:     number
  status:           'active' | 'completed' | 'skipped'
  created_at:       string
  completed_at:     string | null
  progress_count:   number
  total_count:      number
  pct:              number
}

export interface Pattern {
  id:          string
  category:    'champion' | 'death' | 'trend' | 'habit' | 'pool'
  title:       string
  description: string
  evidence:    string
  confidence:  number
  actionable:  string
}

export interface Insight {
  rank:       number
  text:       string
  evidence:   string
  category:   'positive' | 'negative' | 'neutral'
  confidence: number
}

export interface Recommendation {
  rank:        number
  title:       string
  body:        string
  why:         string
  impact:      string
  impact_pct:  number
  confidence:  number
  difficulty:  string
  goal_str:    string
  metric_key:  string | null
}

export interface SessionMatch {
  match_id:      string
  champion:      string
  role:          string
  is_win:        boolean
  kda:           string
  overall_score: number | null
  best_dim:      string | null
  worst_dim:     string | null
}

export interface SessionSummary {
  has_session:   boolean
  total_games:   number
  wins:          number
  losses:        number
  avg_score:     number | null
  best_aspect:   string | null
  worst_aspect:  string | null
  goal_progress: string | null
  tip:           string | null
  session_label: string
  matches:       SessionMatch[]
}

export interface MemoryEntry {
  goal_title:   string
  status:       'active' | 'completed' | 'skipped'
  created_at:   string
  completed_at: string | null
  metric_key:   string
}

export interface KnowledgeResponse {
  has_data:        boolean
  role:            string
  total_matches:   number
  session:         SessionSummary
  active_goal:     Goal | null
  memory:          MemoryEntry[]
  patterns:        Pattern[]
  insights:        Insight[]
  recommendations: Recommendation[]
  confidence:      string
  games_needed_msg: string | null
}
