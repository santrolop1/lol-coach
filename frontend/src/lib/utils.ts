import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

export function formatScore(score: number | null | undefined): string {
  if (score == null) return '—'
  return score.toFixed(0)
}

export function formatPercent(value: number | null | undefined): string {
  if (value == null) return '—'
  return `${value.toFixed(1)}%`
}

export function scoreToColor(score: number): string {
  if (score >= 75) return 'text-emerald-400'
  if (score >= 55) return 'text-yellow-400'
  return 'text-red-400'
}

export function scoreToBg(score: number): string {
  if (score >= 75) return 'bg-emerald-400/10 text-emerald-400'
  if (score >= 55) return 'bg-yellow-400/10 text-yellow-400'
  return 'bg-red-400/10 text-red-400'
}
