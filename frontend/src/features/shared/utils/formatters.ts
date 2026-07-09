import type { Trend, ConfidenceLevel } from '@/features/shared/types/api'

// ── Scores ─────────────────────────────────────────────────────────────────────

export type ScoreGrade = 'S' | 'A' | 'B' | 'C' | 'D'

export function getGrade(score: number): ScoreGrade {
  if (score >= 80) return 'S'
  if (score >= 70) return 'A'
  if (score >= 60) return 'B'
  if (score >= 50) return 'C'
  return 'D'
}

export function getScoreColor(score: number): string {
  if (score >= 80) return 'text-emerald-400'
  if (score >= 70) return 'text-blue-400'
  if (score >= 60) return 'text-yellow-400'
  if (score >= 50) return 'text-orange-400'
  return 'text-red-400'
}

export function getScoreStroke(score: number): string {
  if (score >= 80) return '#34d399'   // emerald-400
  if (score >= 70) return '#60a5fa'   // blue-400
  if (score >= 60) return '#facc15'   // yellow-400
  if (score >= 50) return '#fb923c'   // orange-400
  return '#f87171'                    // red-400
}

export function getGradeColor(grade: ScoreGrade): string {
  const map: Record<ScoreGrade, string> = {
    S: 'text-emerald-400',
    A: 'text-blue-400',
    B: 'text-yellow-400',
    C: 'text-orange-400',
    D: 'text-red-400'
  }
  return map[grade]
}

// ── Trend ──────────────────────────────────────────────────────────────────────

export function formatTrend(trend: Trend | null | undefined): string {
  if (!trend) return '—'
  const map: Record<Trend, string> = {
    improving: '↑ Mejorando',
    stable:    '→ Estable',
    declining: '↓ Bajando'
  }
  return map[trend]
}

export function getTrendColor(trend: Trend | null | undefined): string {
  if (!trend) return 'text-muted-foreground'
  const map: Record<Trend, string> = {
    improving: 'text-emerald-400',
    stable:    'text-muted-foreground',
    declining: 'text-red-400'
  }
  return map[trend]
}

// ── Confidence ─────────────────────────────────────────────────────────────────

export function formatConfidence(level: ConfidenceLevel | string | null | undefined): string {
  if (!level) return '—'
  const map: Record<string, string> = {
    reliable:      'Confiable',
    low_sample:    'Muestra baja',
    insufficient:  'Insuficiente'
  }
  return map[level] ?? level
}

// ── Problemas ──────────────────────────────────────────────────────────────────

const PROBLEM_LABELS: Record<string, string> = {
  HIGH_DEATHS:       'Demasiadas muertes',
  LOW_CS:            'Farm insuficiente',
  LOW_CS_PM:         'CS por minuto bajo',
  LOW_KP:            'Baja participación en kills',
  LOW_VISION:        'Visión deficiente',
  POOR_OBJECTIVES:   'Pocos objetivos',
  LOW_DAMAGE:        'Daño insuficiente',
  INCONSISTENCY:     'Alto nivel de inconsistencia',
  LOW_GOLD_INCOME:   'Ingreso de oro bajo',
  LOW_PRESSURE:      'Poca presión en mapa',
  POOR_TEAMFIGHTS:   'Teamfights deficientes',
}

export function formatProblem(code: string | null | undefined): string {
  if (!code) return ''
  return PROBLEM_LABELS[code] ?? code.replace(/_/g, ' ')
}

// ── Números ────────────────────────────────────────────────────────────────────

export function formatScore(score: number | null | undefined): string {
  if (score == null) return '—'
  return score.toFixed(0)
}

export function formatPercent(value: number | null | undefined, decimals = 1): string {
  if (value == null) return '—'
  return `${value.toFixed(decimals)}%`
}

export function formatNumber(value: number | null | undefined, decimals = 1): string {
  if (value == null) return '—'
  return value.toFixed(decimals)
}
