import { cn } from '@/lib/utils'
import { getScoreStroke } from '@/features/shared/utils/formatters'

export interface LoLTrendChartProps {
  data:       number[]
  width?:     number
  height?:    number
  className?: string
  showDots?:  boolean
}

function normalize(values: number[]): number[] {
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min
  if (range === 0) return values.map(() => 0.5)
  return values.map((v) => (v - min) / range)
}

function buildPath(points: [number, number][]): string {
  if (points.length < 2) return ''

  let d = `M ${points[0][0]} ${points[0][1]}`

  for (let i = 1; i < points.length; i++) {
    const prev = points[i - 1]
    const curr = points[i]
    const cpX = (prev[0] + curr[0]) / 2
    d += ` C ${cpX} ${prev[1]}, ${cpX} ${curr[1]}, ${curr[0]} ${curr[1]}`
  }

  return d
}

export function LoLTrendChart({
  data,
  width  = 120,
  height = 40,
  className,
  showDots = true
}: LoLTrendChartProps) {
  if (data.length < 2) {
    return (
      <div
        className={cn('flex items-center justify-center text-muted-foreground/30 text-xs', className)}
        style={{ width, height }}
      >
        sin datos
      </div>
    )
  }

  const PAD   = 4
  const inner = { w: width - PAD * 2, h: height - PAD * 2 }

  const normalized = normalize(data)
  const points: [number, number][] = normalized.map((v, i) => [
    PAD + (i / (data.length - 1)) * inner.w,
    PAD + (1 - v) * inner.h
  ])

  const lastScore  = data[data.length - 1]
  const strokeColor = getScoreStroke(lastScore)
  const pathD      = buildPath(points)

  // Gradiente bajo la curva
  const areaD = `${pathD} L ${points[points.length - 1][0]} ${height - PAD} L ${PAD} ${height - PAD} Z`

  const uid = `chart-${Math.random().toString(36).slice(2, 7)}`

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={cn('overflow-visible', className)}
      aria-label="Gráfico de tendencia"
      role="img"
    >
      <defs>
        <linearGradient id={uid} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%"   stopColor={strokeColor} stopOpacity="0.25" />
          <stop offset="100%" stopColor={strokeColor} stopOpacity="0"    />
        </linearGradient>
      </defs>

      {/* Area fill */}
      <path d={areaD} fill={`url(#${uid})`} />

      {/* Line */}
      <path
        d={pathD}
        fill="none"
        stroke={strokeColor}
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Dots */}
      {showDots && points.map(([x, y], i) => (
        <circle
          key={i}
          cx={x}
          cy={y}
          r={i === points.length - 1 ? 3 : 1.5}
          fill={i === points.length - 1 ? strokeColor : 'hsl(var(--border))'}
          stroke={i === points.length - 1 ? strokeColor : 'none'}
        />
      ))}
    </svg>
  )
}
