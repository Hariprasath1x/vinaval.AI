import { Construction } from 'lucide-react'

interface ComingSoonTabProps {
  icon: string
  name: string
  description: string
}

export default function ComingSoonTab({ icon, name, description }: ComingSoonTabProps) {
  return (
    <div className="flex flex-col items-center justify-center py-24 px-6 text-center">
      <div className="relative mb-6">
        <span className="text-6xl">{icon}</span>
        <div className="absolute -bottom-1 -right-1 w-7 h-7 rounded-full bg-amber-500/20 border border-amber-500/40 flex items-center justify-center">
          <Construction className="w-3.5 h-3.5 text-amber-400" />
        </div>
      </div>

      <h2 className="font-display text-2xl font-bold text-white mb-2">{name}</h2>
      <p className="text-slate-400 text-sm max-w-sm mb-8">{description}</p>

      <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/10 border border-amber-500/30">
        <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
        <span className="text-amber-300 text-xs font-medium">Coming Soon</span>
      </div>
    </div>
  )
}
