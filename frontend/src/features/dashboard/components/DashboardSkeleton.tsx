import { Skeleton } from '@/components/ui/skeleton'

function HeroSkeleton() {
  return (
    <div className="rounded-2xl border border-border bg-card p-6 space-y-3">
      <Skeleton className="h-8 w-48" />
      <div className="flex gap-2">
        <Skeleton className="h-6 w-28 rounded-md" />
        <Skeleton className="h-6 w-24 rounded-full" />
      </div>
    </div>
  )
}

function RoleCardSkeleton() {
  return (
    <div className="rounded-xl border border-border bg-card overflow-hidden">
      {/* header */}
      <div className="border-b border-border px-5 py-3 flex justify-between">
        <Skeleton className="h-3 w-10" />
        <Skeleton className="h-3 w-16" />
      </div>
      <div className="p-5 space-y-4">
        {/* Score ring placeholder */}
        <div className="flex items-center gap-4">
          <Skeleton className="h-24 w-24 rounded-full" />
          <div className="space-y-2">
            <Skeleton className="h-7 w-16 rounded" />
            <Skeleton className="h-3 w-24" />
          </div>
        </div>
        {/* Metrics */}
        <div className="grid grid-cols-3 gap-2">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-14 rounded-lg" />
          ))}
        </div>
        {/* Problem + priority */}
        <Skeleton className="h-9 rounded-lg" />
        <Skeleton className="h-9 rounded-lg" />
      </div>
    </div>
  )
}

export function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <HeroSkeleton />
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <RoleCardSkeleton />
        <RoleCardSkeleton />
      </div>
    </div>
  )
}
