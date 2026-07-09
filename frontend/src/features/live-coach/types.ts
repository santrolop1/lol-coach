/**
 * Tipos TypeScript del Live Coach — espejo de los modelos Python.
 * Nunca contiene lógica — solo estructuras de datos.
 */

export interface PlayerSnapshot {
  level: number
  gold: number
  kills: number
  deaths: number
  assists: number
  cs: number
  hp_pct: number
  is_dead: boolean
  items: string[]
}

export interface WidgetData {
  id: string
  title: string
  lines: string[]
  priority: number
  visible: boolean
  icon: string
  highlight: boolean
  ttl: number
}

export interface NotificationData {
  title: string
  lines: string[]
  priority: number
  highlight: boolean
}

export interface CoachObjective {
  id: string
  title: string
  description: string
  action_verb: string
  highlight: boolean
  priority: number
}

export interface CoachMission {
  id: string
  title: string
  description: string
  state: 'active' | 'success' | 'failed' | 'expired'
  progress_pct: number
  progress_current: number
  progress_target: number
  progress_unit: string
}

export interface TimelineNext {
  id: string
  time_minutes: number
  title: string
  description: string
  type: string
}

export interface CoachRecommendation {
  id: string
  title: string
  reason: string
  type: string
  priority: number
}

export interface CoachIntelligence {
  state: string
  phase: string
  situation: string
  objective: CoachObjective | null
  mission: CoachMission | null
  timeline_next: TimelineNext | null
  recommendation: CoachRecommendation | null
  is_power_spike: boolean
  is_recall_window: boolean
  coach_mode: string
}

export interface CurrentDecision {
  id: string
  type: string
  title: string
  explanation: string
  action: string
  confidence: number
  confidence_pct: number
  priority: number
  origin: string
  reasons: string[]
  champion_specific: boolean
  state: string
  duration_seconds: number
  age_seconds: number
}

export interface LiveCoachState {
  active: boolean
  champion: string
  role: string
  game_time: number
  phase: 'idle' | 'loading' | 'in_game' | 'post_game'
  provider_connected: boolean
  player: PlayerSnapshot
  widgets: WidgetData[]
  notification: NotificationData | null
  compact_mode: boolean
  timestamp: number
  intelligence: CoachIntelligence | null
  current_decision: CurrentDecision | null
}

export interface DemoScenario {
  id: string
  label: string
  description: string
  phase: string
  current: boolean
}

export interface DemoState {
  active: boolean
  current_scenario: string
  champion: string
  scenario_info: { label: string; description: string; phase: string }
  scenarios: DemoScenario[]
}

export interface OverlayConfigData {
  x: number
  y: number
  width: number
  height: number
  opacity: number
  scale: number
  compact_mode: boolean
  always_on_top: boolean
  monitor_index: number
  widgets_enabled: Record<string, boolean>
  tip_interval_seconds: number
  detail_level: 'minimal' | 'normal' | 'detailed'
  auto_hide_on_idle: boolean
}

export const DEFAULT_STATE: LiveCoachState = {
  active: false,
  champion: '',
  role: '',
  game_time: 0,
  phase: 'idle',
  provider_connected: false,
  player: { level: 1, gold: 0, kills: 0, deaths: 0, assists: 0, cs: 0, hp_pct: 1, is_dead: false, items: [] },
  widgets: [],
  notification: null,
  compact_mode: false,
  timestamp: 0,
  intelligence: null,
  current_decision: null,
}
