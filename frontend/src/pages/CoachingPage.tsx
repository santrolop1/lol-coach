import { Brain } from 'lucide-react'

export default function CoachingPage() {
  return <ComingSoon icon={Brain} title="Coaching" description="Análisis de prioridades, score multidimensional y plan de entrenamiento." sprint="E-4" />
}

function ComingSoon({ icon: Icon, title, description, sprint }: {
  icon: React.ElementType; title: string; description: string; sprint: string
}) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 p-8 text-center">
      <div className="rounded-xl bg-secondary p-5">
        <Icon className="h-10 w-10 text-muted-foreground" />
      </div>
      <div>
        <h2 className="text-lg font-semibold">{title}</h2>
        <p className="mt-1 text-sm text-muted-foreground max-w-xs">{description}</p>
      </div>
      <span className="text-xs font-mono text-muted-foreground/50 bg-secondary px-2 py-1 rounded">
        Sprint {sprint}
      </span>
    </div>
  )
}
