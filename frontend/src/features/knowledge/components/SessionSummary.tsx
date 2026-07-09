import { motion } from 'framer-motion'
import { Clock, Swords, Star, AlertTriangle } from 'lucide-react'
import { LoLScorePill } from '@/components/lol/LoLScoreBadge'
import { cn } from '@/lib/utils'
import type { SessionSummary as SessionSummaryType } from '@/features/knowledge/types'

function MatchDot({ match }: { match: SessionSummaryType['matches'][0] }) {
  const hue = match.champion.split('').reduce((a, c) => a + c.charCodeAt(0), 0) % 360
  return (
    <div className="flex items-center gap-2">
      <div
        className={cn('h-7 w-7 shrink-0 rounded-md flex items-center justify-center text-[10px] font-bold text-white border-2',
          match.is_win ? 'border-emerald-500/50' : 'border-red-500/50'
        )}
        style={{ backgroundColor: `hsl(${hue} 50% 32%)` }}
      >
        {match.champion.slice(0, 2).toUpperCase()}
      </div>
      <div className="min-w-0">
        <p className="text-xs font-medium leading-none">{match.champion}</p>
        <p className="text-[10px] text-muted-foreground mt-0.5">{match.kda}</p>
      </div>
      {match.overall_score != null && (
        <LoLScorePill score={match.overall_score} className="ml-auto shrink-0" />
      )}
    </div>
  )
}

interface SessionSummaryProps {
  session: SessionSummaryType
}

export function SessionSummary({ session }: SessionSummaryProps) {
  if (!session.has_session) return null

  const winrate = session.total_games > 0 ? session.wins / session.total_games : 0

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35 }}
      className="rounded-2xl border border-primary/15 bg-card p-5 space-y-4"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary/15 border border-primary/25">
            <Clock className="h-4 w-4 text-primary" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-wide font-semibold">Sesión de hoy</p>
            <p className="text-sm font-bold leading-none mt-0.5">
              {session.total_games} partidas · {session.wins}V–{session.losses}D
            </p>
          </div>
        </div>
        {session.avg_score != null && (
          <LoLScorePill score={session.avg_score} />
        )}
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded-lg border bg-card/50 p-2.5 text-center">
          <p className="text-[10px] text-muted-foreground uppercase tracking-wide">Winrate</p>
          <p className={cn('text-sm font-bold', winrate >= 0.5 ? 'text-emerald-400' : 'text-red-400')}>
            {Math.round(winrate * 100)}%
          </p>
        </div>
        {session.best_aspect && (
          <div className="rounded-lg border bg-emerald-500/5 border-emerald-500/20 p-2.5 text-center">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wide flex items-center justify-center gap-1">
              <Star className="h-2.5 w-2.5 text-emerald-400" /> Lo mejor
            </p>
            <p className="text-xs font-semibold text-emerald-400">{session.best_aspect}</p>
          </div>
        )}
        {session.worst_aspect && (
          <div className="rounded-lg border bg-red-500/5 border-red-500/20 p-2.5 text-center">
            <p className="text-[10px] text-muted-foreground uppercase tracking-wide flex items-center justify-center gap-1">
              <Swords className="h-2.5 w-2.5 text-red-400" /> Por mejorar
            </p>
            <p className="text-xs font-semibold text-red-400">{session.worst_aspect}</p>
          </div>
        )}
      </div>

      {/* Matches list */}
      {session.matches.length > 0 && (
        <div className="space-y-1.5">
          {session.matches.map((m, i) => (
            <MatchDot key={m.match_id || i} match={m} />
          ))}
        </div>
      )}

      {/* Goal progress */}
      {session.goal_progress && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground border-t border-border/50 pt-3">
          <span>Objetivo:</span>
          <span className="font-medium text-foreground">{session.goal_progress}</span>
        </div>
      )}

      {/* Tip */}
      {session.tip && (
        <div className="flex items-start gap-2 rounded-lg bg-yellow-500/8 border border-yellow-500/20 px-3 py-2">
          <AlertTriangle className="h-3.5 w-3.5 text-yellow-400 mt-0.5 shrink-0" />
          <p className="text-xs text-yellow-300/80">{session.tip}</p>
        </div>
      )}
    </motion.div>
  )
}
