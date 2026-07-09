export interface DraftResponse {
  lcu_connected:  boolean
  phase:          string | null
  phase_label:    string
  role:           string | null
  role_supported: boolean
  session:        Record<string, unknown> | null
  advice:         DraftAdvice | null
  champion_pool:  ChampionPoolData | null
}

export interface DraftAdvice {
  picks?:         string[]
  bans?:          string[]
  notes?:         string[]
  role?:          string
  [key: string]:  unknown
}

export interface ChampionPoolData {
  champions?:    ChampionEntry[]
  role?:         string
  [key: string]: unknown
}

export interface ChampionEntry {
  champion: string
  name?:    string   // alias opcional
  games:    number
  winrate:  number   // 0.0 – 1.0
  grade?:   string
  [key: string]: unknown
}
