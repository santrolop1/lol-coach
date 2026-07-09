import { cn } from '@/lib/utils'
import { LoLScorePill } from '@/components/lol/LoLScoreBadge'

export interface LoLChampionCardProps {
  champion:   string
  role?:      string
  score?:     number | null
  winrate?:   number | null
  games?:     number
  kda?:       string
  isWin?:     boolean
  size?:      'sm' | 'md' | 'lg'
  selected?:  boolean
  onClick?:   () => void
  className?: string
}

const SIZE_WRAP  = { sm: 'gap-2 p-2', md: 'gap-3 p-3', lg: 'gap-4 p-4' }
const SIZE_ICON  = { sm: 'h-7 w-7 text-sm', md: 'h-9 w-9 text-base', lg: 'h-12 w-12 text-lg' }
const SIZE_NAME  = { sm: 'text-xs', md: 'text-sm', lg: 'text-base' }
const SIZE_META  = { sm: 'text-[10px]', md: 'text-xs', lg: 'text-sm' }

function ChampionAvatar({ name, size }: { name: string; size: 'sm' | 'md' | 'lg' }) {
  const initials = name.slice(0, 2).toUpperCase()
  // Colores deterministicos por campeón (hash simple)
  const hue = name.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0) % 360

  return (
    <div
      className={cn(
        'flex shrink-0 items-center justify-center rounded-lg font-bold text-white',
        SIZE_ICON[size]
      )}
      style={{ backgroundColor: `hsl(${hue} 60% 35%)` }}
      aria-label={name}
    >
      {initials}
    </div>
  )
}

export function LoLChampionCard({
  champion, role, score, winrate, games, kda, isWin,
  size = 'md', selected = false, onClick, className
}: LoLChampionCardProps) {
  const Tag = onClick ? 'button' : 'div'

  return (
    <Tag
      className={cn(
        'flex items-center rounded-lg border transition-colors w-full text-left',
        SIZE_WRAP[size],
        selected
          ? 'bg-primary/15 border-primary/40'
          : 'bg-card border-border hover:border-primary/25 hover:bg-card/80',
        onClick && 'cursor-pointer',
        className
      )}
      onClick={onClick}
    >
      {/* Avatar */}
      <ChampionAvatar name={champion} size={size} />

      {/* Info */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={cn('font-medium truncate', SIZE_NAME[size])}>{champion}</span>
          {isWin != null && (
            <span className={cn('shrink-0 font-semibold', SIZE_META[size], isWin ? 'text-emerald-400' : 'text-red-400')}>
              {isWin ? 'V' : 'D'}
            </span>
          )}
        </div>
        <div className={cn('flex items-center gap-1.5 text-muted-foreground mt-0.5', SIZE_META[size])}>
          {role    && <span>{role}</span>}
          {kda     && <><span className="text-muted-foreground/30">·</span><span>{kda}</span></>}
          {games   != null && <><span className="text-muted-foreground/30">·</span><span>{games}g</span></>}
          {winrate != null && (
            <><span className="text-muted-foreground/30">·</span>
            <span className={winrate >= 50 ? 'text-emerald-400' : 'text-red-400'}>
              {winrate.toFixed(0)}%
            </span></>
          )}
        </div>
      </div>

      {/* Score */}
      {score != null && <LoLScorePill score={score} />}
    </Tag>
  )
}
