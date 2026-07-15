import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Plus, ArrowRight, Sparkles, Clock, BookOpen, ChevronRight } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { getExamById, SubjectInfo } from '../constants/exams'
import { spaceService } from '../services/spaceService'
import { SubjectCardSkeleton, SpaceListSkeleton } from '../components/Skeleton'
import type { Space } from '../types/space'
import Navbar from '../components/Navbar'

const MODULE_PREVIEWS = [
  { icon: '📖', label: 'Learn' },
  { icon: '📝', label: 'Practice' },
  { icon: '🃏', label: 'Flashcards' },
  { icon: '🧪', label: 'Exam Lab' },
  { icon: '📊', label: 'Reports' },
  { icon: '🗒️', label: 'Notes' },
]

export default function Dashboard() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const examId = user?.selected_exam

  const [spaces, setSpaces] = useState<Space[]>([])
  const [spacesLoading, setSpacesLoading] = useState(true)

  // Redirect to exam selection if no exam picked yet
  useEffect(() => {
    if (user !== null && !examId) {
      navigate('/select-exam', { replace: true })
    }
  }, [examId, navigate, user])

  // Fetch existing spaces for this user
  useEffect(() => {
    if (!user) return
    setSpacesLoading(true)
    spaceService.list()
      .then(setSpaces)
      .catch(() => setSpaces([]))
      .finally(() => setSpacesLoading(false))
  }, [user])

  const exam = examId ? getExamById(examId) : undefined
  if (!exam) return null

  // Build a lookup: subject name → space
  const spaceBySubject = Object.fromEntries(spaces.map((s) => [s.subject, s]))

  // Recent spaces (most recently updated, same exam, max 3)
  const recentSpaces = spaces
    .filter((s) => s.exam_id === examId)
    .slice(0, 4)

  return (
    <div className="min-h-screen bg-surface-900" style={{ backgroundColor: 'var(--bg)' }}>
      <Navbar examName={exam.name} />

      <main className="relative z-10 max-w-5xl mx-auto px-4 sm:px-6 py-10">

        {/* ── Welcome banner ───────────────────── */}
        <div className="glass-card p-6 md:p-8 mb-8 flex flex-col md:flex-row items-start md:items-center justify-between gap-5">
          <div>
            <div className="tag mb-3">
              <span className="glow-dot" />
              {exam.tag}
            </div>
            <h1 className="text-2xl md:text-3xl font-semibold text-white mb-1.5">
              Welcome back, <span style={{ color: 'var(--accent)' }}>{user?.name?.split(' ')[0]}</span> 👋
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              You are preparing for <strong className="text-white font-medium">{exam.name}</strong>. Pick a subject to open your Learning Space.
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

        {/* ── Recent Spaces ─────────────────────── */}
        {(spacesLoading || recentSpaces.length > 0) && (
          <div className="mb-10">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                <Clock className="w-4 h-4 text-slate-500" />
                Recent Spaces
              </h2>
              {recentSpaces.length > 0 && (
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{recentSpaces.length} active</span>
              )}
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              {spacesLoading
                ? [1, 2, 3, 4].map((i) => <SpaceListSkeleton key={i} />)
                : recentSpaces.map((space) => {
                    const subjectInfo = exam.subjects.find((s) => s.name === space.subject)
                    return (
                      <RecentSpaceCard
                        key={space.id}
                        space={space}
                        subjectInfo={subjectInfo}
                        onClick={() => navigate(`/space/${space.id}`)}
                      />
                    )
                  })}
            </div>
          </div>
        )}

        {/* ── Subjects Grid ────────────────────── */}
        <div className="mb-12">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">
              {exam.name} Subjects
            </h2>
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{exam.subjects.length} subjects</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {spacesLoading
              ? exam.subjects.map((_, i) => <SubjectCardSkeleton key={i} />)
              : exam.subjects.map((subject: SubjectInfo) => (
                  <SubjectCard
                    key={subject.name}
                    subject={subject}
                    examId={exam.id}
                    existingSpace={spaceBySubject[subject.name]}
                  />
                ))}
          </div>
        </div>

        {/* ── What's inside a Learning Space ───── */}
        <div className="glass-card p-6 md:p-8">
          <div className="flex items-center gap-2 mb-6">
            <Sparkles className="w-5 h-5" style={{ color: 'var(--accent)' }} />
            <h2 className="text-lg font-semibold text-white">
              What's inside a Learning Space?
            </h2>
          </div>
          <div className="grid grid-cols-3 sm:grid-cols-6 gap-3">
            {MODULE_PREVIEWS.map((mod) => (
              <div key={mod.label} className="flex flex-col items-center gap-2 py-4 px-3 rounded-xl border transition-all"
                   style={{ backgroundColor: 'var(--bg-elevated)', borderColor: 'var(--border-soft)' }}>
                <span className="text-2xl">{mod.icon}</span>
                <span className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>{mod.label}</span>
              </div>
            ))}
          </div>
          <p className="text-xs mt-5 text-center" style={{ color: 'var(--text-dim)' }}>
            Every Learning Space comes with all 7 modules — AI chat, practice tests, flashcards, exam lab, reports, notes, and export.
          </p>
        </div>
      </main>
    </div>
  )
}

// ── Recent Space Card ──────────────────────────────────────────────────────────
function RecentSpaceCard({
  space,
  subjectInfo,
  onClick,
}: {
  space: Space
  subjectInfo: SubjectInfo | undefined
  onClick: () => void
}) {
  const timeAgo = (dateStr: string) => {
    const diff = Date.now() - new Date(dateStr).getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 60) return `${mins}m ago`
    const hrs = Math.floor(mins / 60)
    if (hrs < 24) return `${hrs}h ago`
    return `${Math.floor(hrs / 24)}d ago`
  }

  return (
    <button
      onClick={onClick}
      className="feature-card flex items-center gap-3 text-left group w-full"
    >
      <div className={`w-10 h-10 rounded-xl ${subjectInfo?.bgClass ?? 'bg-brand-500/10'} border ${subjectInfo?.borderClass ?? 'border-brand-500/20'} flex items-center justify-center text-xl flex-shrink-0`}>
        {subjectInfo?.icon ?? '📚'}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-white truncate group-hover:text-white transition-colors">
          {space.subject}
        </p>
        <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{timeAgo(space.updated_at)}</p>
      </div>
      <ChevronRight className="w-4 h-4 flex-shrink-0 transition-colors opacity-50 group-hover:opacity-100" style={{ color: 'var(--accent)' }} />
    </button>
  )
}

// ── Subject Card ──────────────────────────────────────────────────────────────
function SubjectCard({
  subject,
  examId,
  existingSpace,
}: {
  subject: SubjectInfo
  examId: string
  existingSpace?: Space
}) {
  const navigate = useNavigate()

  const handleClick = () => {
    if (existingSpace) {
      navigate(`/space/${existingSpace.id}`)
    } else {
      navigate(`/space/new?exam=${examId}&subject=${encodeURIComponent(subject.name)}`)
    }
  }

  return (
    <div
      className="feature-card group relative cursor-pointer"
      onClick={handleClick}
      id={`subject-card-${subject.name.toLowerCase().replace(/\s+/g, '-')}`}
    >
      {/* Existing space indicator */}
      {existingSpace && (
        <div className="absolute top-3 right-3 flex items-center gap-1.5 px-2 py-0.5 rounded-full"
             style={{ backgroundColor: 'var(--green-soft)', border: '1px solid rgba(74,222,128,0.2)' }}>
          <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: 'var(--green)' }} />
          <span className="text-xs font-medium" style={{ color: 'var(--green)' }}>Active</span>
        </div>
      )}

      {/* Icon */}
      <div className={`w-12 h-12 rounded-xl ${subject.bgClass} border ${subject.borderClass} flex items-center justify-center text-2xl mb-4`}>
        {subject.icon}
      </div>

      {/* Name */}
      <h3 className="font-medium text-base text-white mb-1 group-hover:text-white transition-colors">{subject.name}</h3>
      <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{examId} · Learning Space</p>

      {/* CTA hint */}
      <div className="mt-4 flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity"
           style={{ color: 'var(--text-muted)' }}>
        {existingSpace ? (
          <>
            <BookOpen className="w-3.5 h-3.5" />
            <span className="text-xs font-medium">Continue Learning</span>
            <ArrowRight className="w-3 h-3" />
          </>
        ) : (
          <>
            <Plus className="w-3.5 h-3.5" />
            <span className="text-xs font-medium">Create Space</span>
            <ArrowRight className="w-3 h-3" />
          </>
        )}
      </div>
    </div>
  )
}
