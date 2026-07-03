import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, BookOpen, ArrowRight, Sparkles } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { getExamById, SubjectInfo } from '../constants/exams'
import Navbar from '../components/Navbar'

const MODULE_PREVIEWS = [
  { icon: '📖', label: 'Learn' },
  { icon: '📝', label: 'Practice' },
  { icon: '🧪', label: 'Exam Lab' },
  { icon: '📊', label: 'Reports' },
  { icon: '🗒️', label: 'Notes' },
  { icon: '📤', label: 'Export' },
]

export default function Dashboard() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const examId = user?.selected_exam

  // Redirect to exam selection if no exam picked yet
  useEffect(() => {
    if (!examId) {
      navigate('/select-exam', { replace: true })
    }
  }, [examId])

  const exam = examId ? getExamById(examId) : undefined

  if (!exam) return null

  return (
    <div className="min-h-screen bg-surface-900">
      {/* Background orbs */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="orb w-[500px] h-[500px] bg-brand-800 top-0 right-[-150px]" />
        <div className="orb w-[350px] h-[350px] bg-purple-900 bottom-0 left-[-100px]" />
      </div>

      <Navbar examName={exam.name} />

      <main className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 py-10">

        {/* ── Welcome banner ───────────────────── */}
        <div className="glass-card rounded-3xl p-6 md:p-8 mb-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-5">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <div className="glow-dot animate-pulse-slow" />
              <span className="text-xs text-brand-300 font-medium tracking-wide uppercase">{exam.tag}</span>
            </div>
            <h1 className="font-display text-2xl md:text-3xl font-bold text-white mb-1">
              Welcome back, <span className="gradient-text">{user?.name?.split(' ')[0]}</span> 👋
            </h1>
            <p className="text-slate-400 text-sm">
              You are preparing for <strong className="text-white">{exam.name}</strong>. Pick a subject to start a Learning Space.
            </p>
          </div>
          <button
            id="switch-exam-btn"
            onClick={() => navigate('/select-exam')}
            className="btn-outline text-sm py-2 px-4 flex-shrink-0"
          >
            Switch Exam
          </button>
        </div>

        {/* ── Subjects Grid ────────────────────── */}
        <div className="mb-12">
          <div className="flex items-center justify-between mb-5">
            <h2 className="font-display text-lg font-semibold text-white">
              {exam.name} Subjects
            </h2>
            <span className="text-xs text-slate-500">{exam.subjects.length} subjects</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {exam.subjects.map((subject: SubjectInfo) => (
              <SubjectCard key={subject.name} subject={subject} examId={exam.id} />
            ))}
          </div>
        </div>

        {/* ── What's inside a Learning Space ───── */}
        <div className="glass-card rounded-3xl p-6 md:p-8">
          <div className="flex items-center gap-2 mb-6">
            <Sparkles className="w-5 h-5 text-brand-400" />
            <h2 className="font-display text-lg font-semibold text-white">
              What's inside a Learning Space?
            </h2>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {MODULE_PREVIEWS.map((mod) => (
              <div key={mod.label} className="flex flex-col items-center gap-2 py-4 px-3 rounded-xl bg-white/[0.03] border border-white/5 hover:border-brand-500/20 hover:bg-brand-500/5 transition-all">
                <span className="text-2xl">{mod.icon}</span>
                <span className="text-xs text-slate-400 font-medium">{mod.label}</span>
              </div>
            ))}
          </div>
          <p className="text-slate-500 text-xs mt-5 text-center">
            Every Learning Space comes with all 6 modules — AI chat, practice tests, exam lab, reports, notes, and export.
          </p>
        </div>
      </main>
    </div>
  )
}

// ── Subject Card ──────────────────────────────────────────────────────────────
function SubjectCard({ subject, examId }: { subject: SubjectInfo; examId: string }) {
  const navigate = useNavigate()

  return (
    <div
      className={`
        group relative rounded-2xl p-5 border transition-all duration-300 cursor-pointer
        glass-card hover:border-brand-500/30 hover:-translate-y-1 hover:shadow-xl hover:shadow-brand-500/10
      `}
      onClick={() => navigate(`/space/new?exam=${examId}&subject=${encodeURIComponent(subject.name)}`)}
      id={`subject-card-${subject.name.toLowerCase().replace(/\s+/g, '-')}`}
    >
      {/* Icon */}
      <div className={`w-12 h-12 rounded-xl ${subject.bgClass} border ${subject.borderClass} flex items-center justify-center text-2xl mb-4 group-hover:scale-110 transition-transform`}>
        {subject.icon}
      </div>

      {/* Name */}
      <h3 className={`font-semibold text-base mb-1 ${subject.textClass}`}>{subject.name}</h3>
      <p className="text-slate-500 text-xs">{examId} · Learning Space</p>

      {/* Create hint */}
      <div className="mt-4 flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
        <Plus className="w-3.5 h-3.5 text-brand-400" />
        <span className="text-xs text-brand-400 font-medium">Create Space</span>
        <ArrowRight className="w-3 h-3 text-brand-400" />
      </div>
    </div>
  )
}
