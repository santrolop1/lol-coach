import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard, Brain, History, Swords, Settings,
  ChevronRight, Wifi, WifiOff, TrendingUp, Lightbulb, Dumbbell, Zap
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useAppStore } from '@/store/appStore'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

interface NavItem {
  id:    string
  label: string
  icon:  React.ElementType
  href:  string
  badge?: string
}

const NAV_ITEMS: NavItem[] = [
  { id: 'dashboard', label: 'Dashboard',  icon: LayoutDashboard, href: '/'           },
  { id: 'knowledge', label: 'Coach',       icon: Lightbulb,  href: '/knowledge'  },
  { id: 'training',  label: 'Entrena',    icon: Dumbbell,   href: '/training'   },
  { id: 'progress',  label: 'Progreso',   icon: TrendingUp, href: '/progress'   },
  { id: 'coaching',  label: 'Coaching',   icon: Brain,            href: '/coaching'  },
  { id: 'matches',   label: 'Partidas',   icon: History,          href: '/matches'   },
  { id: 'draft',      label: 'Draft',       icon: Swords,           href: '/draft'      },
  { id: 'live-coach', label: 'Live Coach',  icon: Zap,              href: '/live-coach', badge: 'LIVE' },
]

export function Sidebar() {
  const location     = useLocation()
  const [hovered, setHovered] = useState(false)
  const { sidebarPinned, toggleSidebar, lcuConnected } = useAppStore()

  const expanded = sidebarPinned || hovered

  return (
    <motion.nav
      className="relative flex flex-col border-r border-border bg-card z-20 select-none"
      animate={{ width: expanded ? 220 : 64 }}
      transition={{ duration: 0.2, ease: 'easeInOut' }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Logo */}
      <div className="flex h-14 items-center px-4 overflow-hidden">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary/20 border border-primary/30">
          <span className="text-sm font-bold text-primary">LC</span>
        </div>
        <AnimatePresence>
          {expanded && (
            <motion.span
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -8 }}
              transition={{ duration: 0.15 }}
              className="ml-3 text-sm font-semibold whitespace-nowrap overflow-hidden"
            >
              LoL Coach
            </motion.span>
          )}
        </AnimatePresence>
      </div>

      {/* Nav items */}
      <div className="flex flex-col gap-0.5 px-2 flex-1 py-2">
        {NAV_ITEMS.map((item) => {
          const isActive = item.href === '/'
            ? location.pathname === '/'
            : location.pathname.startsWith(item.href)

          const Icon = item.icon

          const navContent = (
            <NavLink
              key={item.id}
              to={item.href}
              className={cn(
                'flex items-center gap-3 rounded-md px-2 py-2 text-sm font-medium transition-colors relative group',
                isActive
                  ? 'bg-primary/15 text-primary'
                  : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
              )}
            >
              {/* Active indicator */}
              {isActive && (
                <motion.div
                  layoutId="nav-active"
                  className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-0.5 rounded-full bg-primary"
                  transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                />
              )}
              <Icon className="h-4 w-4 shrink-0" />
              <AnimatePresence>
                {expanded && (
                  <motion.span
                    initial={{ opacity: 0, x: -6 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -6 }}
                    transition={{ duration: 0.12 }}
                    className="whitespace-nowrap overflow-hidden"
                  >
                    {item.label}
                  </motion.span>
                )}
              </AnimatePresence>

              {/* Badge LCU en draft */}
              {item.id === 'draft' && (
                <span className={cn(
                  'absolute right-2 top-1/2 -translate-y-1/2 h-1.5 w-1.5 rounded-full',
                  lcuConnected ? 'bg-emerald-400' : 'bg-muted-foreground/40'
                )} />
              )}
            </NavLink>
          )

          // Si el sidebar está colapsado, mostrar tooltip
          if (!expanded) {
            return (
              <Tooltip key={item.id} delayDuration={300}>
                <TooltipTrigger asChild>{navContent}</TooltipTrigger>
                <TooltipContent side="right">{item.label}</TooltipContent>
              </Tooltip>
            )
          }

          return navContent
        })}
      </div>

      {/* Footer: Settings + pin */}
      <div className="px-2 pb-3 flex flex-col gap-0.5">
        <div className="mb-1 flex items-center gap-1.5 px-2 py-1">
          {lcuConnected
            ? <Wifi className="h-3 w-3 text-emerald-400 shrink-0" />
            : <WifiOff className="h-3 w-3 text-muted-foreground/50 shrink-0" />
          }
          <AnimatePresence>
            {expanded && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="text-xs text-muted-foreground whitespace-nowrap"
              >
                {lcuConnected ? 'Cliente conectado' : 'Sin cliente'}
              </motion.span>
            )}
          </AnimatePresence>
        </div>

        <NavLink
          to="/settings"
          className={cn(
            'flex items-center gap-3 rounded-md px-2 py-2 text-sm font-medium transition-colors',
            location.pathname === '/settings'
              ? 'bg-primary/15 text-primary'
              : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
          )}
        >
          <Settings className="h-4 w-4 shrink-0" />
          <AnimatePresence>
            {expanded && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="whitespace-nowrap"
              >
                Ajustes
              </motion.span>
            )}
          </AnimatePresence>
        </NavLink>

        {/* Pin toggle */}
        <button
          onClick={toggleSidebar}
          className={cn(
            'flex items-center gap-3 rounded-md px-2 py-2 text-xs transition-colors w-full',
            'text-muted-foreground/50 hover:text-muted-foreground hover:bg-secondary'
          )}
        >
          <ChevronRight
            className={cn('h-3.5 w-3.5 shrink-0 transition-transform', sidebarPinned && 'rotate-180')}
          />
          <AnimatePresence>
            {expanded && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="whitespace-nowrap"
              >
                {sidebarPinned ? 'Colapsar' : 'Fijar'}
              </motion.span>
            )}
          </AnimatePresence>
        </button>
      </div>
    </motion.nav>
  )
}
