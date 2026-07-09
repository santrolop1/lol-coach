import { motion } from 'framer-motion'
import { Lock, CheckCircle2, Zap, Circle } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { SkillNode } from '../types'

const STATUS_CFG = {
  locked:    { ring: 'border-border',            bg: 'bg-secondary/30',     text: 'text-muted-foreground/40' },
  available: { ring: 'border-primary/30',        bg: 'bg-primary/5',        text: 'text-foreground'          },
  active:    { ring: 'border-primary ring-2',    bg: 'bg-primary/10',       text: 'text-foreground'          },
  completed: { ring: 'border-emerald-500/50',    bg: 'bg-emerald-500/8',    text: 'text-foreground'          },
}

const SCORE_COLOR = (s: number) =>
  s >= 70 ? 'text-emerald-400' :
  s >= 55 ? 'text-blue-400'    :
  s >= 40 ? 'text-yellow-400'  :
            'text-red-400'

function SkillIcon({ status }: { status: SkillNode['status'] }) {
  if (status === 'locked')    return <Lock      className="h-3.5 w-3.5" />
  if (status === 'completed') return <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
  if (status === 'active')    return <Zap       className="h-3.5 w-3.5 text-primary" />
  return                             <Circle    className="h-3.5 w-3.5 text-primary/50" />
}

interface SkillTreeProps {
  nodes: SkillNode[]
}

export function SkillTree({ nodes }: SkillTreeProps) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
      {nodes.map((node, i) => {
        const cfg = STATUS_CFG[node.status]
        return (
          <motion.div
            key={node.key}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.25, delay: i * 0.06 }}
            className={cn(
              'rounded-xl border-2 p-3 space-y-2 transition-all',
              cfg.ring, cfg.bg,
              node.status === 'locked' ? 'opacity-40' : ''
            )}
          >
            <div className="flex items-center justify-between">
              <SkillIcon status={node.status} />
              {node.status !== 'locked' && (
                <span className={cn('text-sm font-bold tabular-nums', SCORE_COLOR(node.score))}>
                  {node.score.toFixed(0)}
                </span>
              )}
            </div>

            <div>
              <p className={cn('text-xs font-semibold leading-snug', cfg.text)}>{node.name}</p>
              {node.status !== 'locked' && (
                <p className="text-[11px] text-muted-foreground mt-0.5 leading-relaxed line-clamp-2">
                  {node.description}
                </p>
              )}
            </div>

            {/* Score bar */}
            {node.status !== 'locked' && (
              <div className="h-1 rounded-full bg-border overflow-hidden">
                <motion.div
                  className={cn(
                    'h-full rounded-full',
                    node.score >= 70 ? 'bg-emerald-500' :
                    node.score >= 55 ? 'bg-blue-500'    :
                    node.score >= 40 ? 'bg-yellow-500'  : 'bg-red-500'
                  )}
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.min(100, node.score)}%` }}
                  transition={{ duration: 0.5, delay: i * 0.06 + 0.2 }}
                />
              </div>
            )}

            {node.status === 'active' && (
              <span className="inline-block text-[10px] font-bold text-primary bg-primary/15 rounded px-1.5 py-0.5">
                EN PROGRESO
              </span>
            )}
            {node.status === 'completed' && (
              <span className="inline-block text-[10px] font-bold text-emerald-400 bg-emerald-500/10 rounded px-1.5 py-0.5">
                COMPLETADO
              </span>
            )}
          </motion.div>
        )
      })}
    </div>
  )
}
