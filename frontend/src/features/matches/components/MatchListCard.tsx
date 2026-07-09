import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ChevronRight } from 'lucide-react'
import { LoLScorePill } from '@/components/lol/LoLScoreBadge'
import { cn } from '@/lib/utils'
import type { MatchCard } from '@/features/matches/types'

interface MatchListCardProps {
  card:  MatchCard
  index: number
}

function ChampionAvatar({ name }: { name: string }) {
  const hue = name.split('').reduce((a, c) => a + c.charCodeAt(0), 0) % 360
  return (
    <div
      className="h-10 w-10 shrink-0 rounded-lg flex items-center justify-center text-xs font-bold text-white"
      style={{ backgroundColor: `hsl(${hue} 55% 35%)` }}
    >
      {name.slice(0, 2).toUpperCase()}
    </div>
  )
}

export function MatchListCard({ card, index }: MatchListCardProps) {
  const navigate = useNavigate()

  const resultBorder = card.is_win
    ? 'border-l-2 border-l-emerald-500/60'
    : 'border-l-2 border-l-red-500/60'

  return (
    <motion.button
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3, delay: index * 0.04 }}
      onClick={() => navigate(`/matches/${encodeURIComponent(card.match_id)}`)}
      className={cn(
        'w-full flex items-center gap-3 rounded-lg border bg-card px-3 py-2.5',
        'text-left hover:bg-card/80 hover:border-primary/25 transition-colors',
        'active:scale-[0.99] transition-transform',
        resultBorder
      )}
    >
      <ChampionAvatar name={card.champion} />

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium truncate">{card.champion}</span>
          <span className={cn('text-xs font-bold shrink-0', card.is_win ? 'text-emerald-400' : 'text-red-400')}>
            {card.is_win ? 'V' : 'D'}
          </span>
          <span className="text-xs text-muted-foreground shrink-0">{card.role}</span>
        </div>
        <div className="flex items-center gap-2 mt-0.5 text-xs text-muted-foreground">
          <span className="tabular-nums">{card.kda}</span>
          <span className="text-muted-foreground/30">·</span>
          <span className="text-emerald-400/80">↑ {card.best_dim}</span>
          <span className="text-muted-foreground/30">·</span>
          <span className="text-red-400/80">↓ {card.worst_dim}</span>
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <LoLScorePill score={card.overall_score} />
        <ChevronRight className="h-4 w-4 text-muted-foreground/40" />
      </div>
    </motion.button>
  )
}
