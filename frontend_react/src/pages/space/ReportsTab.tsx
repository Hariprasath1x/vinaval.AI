import { useState, useEffect } from 'react'
import { Loader2, TrendingUp, Target, BookOpen, FlaskConical, RefreshCw } from 'lucide-react'
import { quizService } from '../../services/quizService'
import type { SpaceStats } from '../../types/quiz'

interface ReportsTabProps {
  spaceId: number
  subject: string
  examId: string
}

export default function ReportsTab({ spaceId, subject }: ReportsTabProps) {
  const [stats, setStats] = useState<SpaceStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = () => {
    setLoading(true)
    setError(null)
    quizService.getStats(spaceId)
      .then((s) => { setStats(s); setLoading(false) })
      .catch((e) => { setError(e?.message ?? 'Failed to load stats'); setLoading(false) })
  }

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    quizService.getStats(spaceId)
      .then((s) => { if (!cancelled) { setStats(s); setLoading(false) } })
      .catch((e) => { if (!cancelled) { setError(e?.message ?? 'Failed'); setLoading(false) } })
    return () => { cancelled = true }
  }, [spaceId])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="w-6 h-6 text-brand-400 animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-24 gap-4">
        <p className="text-red-400 text-sm">{error}</p>
        <button onClick={load} className="btn-outline text-sm py-2 px-4">
          <RefreshCw className="w-4 h-4" /> Retry
        </button>
      </div>
    )
  }

  const s = stats!

  if (s.total_all === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center px-4">
        <div className="w-20 h-20 rounded-2xl flex items-center justify-center mb-5"
             style={{ backgroundColor: 'var(--accent-soft)', border: '1px solid rgba(90,127,245,0.2)' }}>
          <TrendingUp className="w-10 h-10" style={{ color: 'var(--accent)' }} />
        </div>
        <h2 className="text-lg font-semibold text-white mb-2">No data yet</h2>
        <p className="text-sm max-w-xs" style={{ color: 'var(--text-muted)' }}>
          Complete some practice questions or an Exam Lab session to see your performance reports here.
        </p>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 tab-panel-enter">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold text-white">{subject} Performance</h2>
        <button
          onClick={load}
          className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          Refresh
        </button>
      </div>

      {/* ── Accuracy Rings ── */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <RingCard
          icon={<Target className="w-4 h-4" />}
          label="Overall"
          pct={s.accuracy_all}
          correct={s.correct_all}
          total={s.total_all}
          color="#5b7fff"
          trackColor="rgba(91,127,255,0.15)"
        />
        <RingCard
          icon={<BookOpen className="w-4 h-4" />}
          label="Practice"
          pct={s.accuracy_practice}
          correct={s.correct_practice}
          total={s.total_practice}
          color="#3b82f6"
          trackColor="rgba(59,130,246,0.15)"
        />
        <RingCard
          icon={<FlaskConical className="w-4 h-4" />}
          label="Exam Lab"
          pct={s.accuracy_exam}
          correct={s.correct_exam}
          total={s.total_exam}
          color="#a78bfa"
          trackColor="rgba(167,139,250,0.15)"
        />
      </div>

      {/* ── Accuracy Bars ── */}
      <div className="glass-card rounded-2xl p-5 mb-5">
        <p className="text-sm font-medium mb-5" style={{ color: 'var(--text)' }}>Accuracy Breakdown</p>
        <div className="space-y-5">
          <AccuracyBar label="Overall" pct={s.accuracy_all} color="var(--accent)" total={s.total_all} correct={s.correct_all} />
          <AccuracyBar label="Practice" pct={s.accuracy_practice} color="#3b82f6" total={s.total_practice} correct={s.correct_practice} />
          <AccuracyBar label="Exam Lab" pct={s.accuracy_exam} color="#a78bfa" total={s.total_exam} correct={s.correct_exam} />
        </div>
      </div>

      {/* ── Topics Practiced ── */}
      {s.topics_practiced.length > 0 && (
        <div className="glass-card rounded-2xl p-5">
          <p className="text-sm font-medium mb-3" style={{ color: 'var(--text)' }}>
            Topics Practiced
            <span className="ml-2 text-xs" style={{ color: 'var(--text-muted)' }}>({s.topics_practiced.length})</span>
          </p>
          <div className="flex flex-wrap gap-2">
            {s.topics_practiced.map((t) => (
              <span key={t} className="tag">
                {t}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Ring Card ──────────────────────────────────────────────────────────────────

function RingCard({
  icon, label, pct, correct, total, color, trackColor,
}: {
  icon: React.ReactNode
  label: string
  pct: number
  correct: number
  total: number
  color: string
  trackColor: string
}) {
  const radius = 36
  const circumference = 2 * Math.PI * radius
  const strokeDashoffset = circumference - (pct / 100) * circumference

  return (
    <div className="glass-card rounded-xl p-4 flex flex-col items-center text-center">
      <div className="relative w-24 h-24 mb-3">
        <svg className="w-24 h-24 -rotate-90" viewBox="0 0 88 88">
          {/* Track */}
          <circle cx="44" cy="44" r={radius} fill="none" stroke={trackColor} strokeWidth="7" />
          {/* Progress */}
          <circle
            cx="44" cy="44" r={radius}
            fill="none"
            stroke={color}
            strokeWidth="7"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            style={{ transition: 'stroke-dashoffset 1s ease-out' }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-lg font-bold text-white">{pct}%</span>
        </div>
      </div>

      <div className="flex items-center gap-1.5 text-slate-400 text-xs mb-1">
        {icon}
        <span className="font-medium">{label}</span>
      </div>
      <div className="text-xs text-slate-500">
        {total === 0 ? 'No attempts' : `${correct}/${total} correct`}
      </div>
    </div>
  )
}

// ── Accuracy Bar ───────────────────────────────────────────────────────────────

function AccuracyBar({
  label, pct, color, total, correct,
}: {
  label: string
  pct: number
  color: string
  total: number
  correct: number
}) {
  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-2">
        <span className="font-medium" style={{ color: 'var(--text)' }}>{label}</span>
        <span style={{ color: 'var(--text-muted)' }}>
          {total === 0 ? '—' : `${correct}/${total} · ${pct}%`}
        </span>
      </div>
      <div className="h-2 w-full rounded-full overflow-hidden" style={{ backgroundColor: 'var(--border-soft)' }}>
        <div
          className="h-2 rounded-full transition-all duration-700"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  )
}
