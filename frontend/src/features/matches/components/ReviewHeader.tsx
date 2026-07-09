import { ArrowLeft, Flag } from 'lucide-react'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import type { MatchReviewResponse } from '@/features/matches/types'

interface ReviewHeaderProps {
  data:    MatchReviewResponse
  onBack:  () => void
}

export function ReviewHeader({ data, onBack }: ReviewHeaderProps) {
  const resultClr = data.is_win ? 'text-emerald-400' : 'text-red-400'
  const resultBg  = data.is_win ? 'bg-emerald-500/10 border-emerald-500/25' : 'bg-red-500/10 border-red-500/25'

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="sticky top-0 z-10 bg-background/80 backdrop-blur-md border-b border-border"
    >
      <div className="flex items-center gap-4 px-6 py-3">
        {/* Back */}
        <Button variant="ghost" size="sm" onClick={onBack} className="shrink-0 -ml-1">
          <ArrowLeft className="h-4 w-4" />
          Partidas
        </Button>

        <div className="h-5 w-px bg-border shrink-0" />

        {/* Champion + role */}
        <div className="flex items-center gap-2.5 min-w-0">
          <div
            className="h-8 w-8 rounded-lg flex items-center justify-center text-xs font-bold text-white shrink-0"
            style={{ backgroundColor: `hsl(${data.champion.split('').reduce((a, c) => a + c.charCodeAt(0), 0) % 360} 55% 35%)` }}
          >
            {data.champion.slice(0, 2).toUpperCase()}
          </div>
          <div className="min-w-0">
            <p className="font-semibold text-sm leading-none truncate">{data.champion}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{data.role} · {data.date}</p>
          </div>
        </div>

        {/* Result badge */}
        <span className={cn('shrink-0 inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-bold', resultBg, resultClr)}>
          {data.is_surrender && <Flag className="h-3 w-3" />}
          {data.is_win ? 'Victoria' : 'Derrota'} · {data.duration}
        </span>

        {/* KDA + CS */}
        <div className="hidden sm:flex items-center gap-4 ml-auto text-sm">
          <span className="tabular-nums font-medium">{data.kda}</span>
          <span className="text-muted-foreground">{data.cs} CS</span>
        </div>
      </div>
    </motion.div>
  )
}
