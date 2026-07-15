import { useEffect, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { ChevronRight, AlertCircle } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { getExamById } from '../constants/exams'
import { spaceService } from '../services/spaceService'
import type { SpaceDetail } from '../types/space'
import Navbar from '../components/Navbar'
import { SpaceHeaderSkeleton } from '../components/Skeleton'
import LearnTab from './space/LearnTab'
import NotesTab from './space/NotesTab'
import PracticeTab from './space/PracticeTab'
import ExamLabTab from './space/ExamLabTab'
import ReportsTab from './space/ReportsTab'
import FlashcardsTab from './space/FlashcardsTab'
import ExportTab from './space/ExportTab'
import MaterialsTab from './space/MaterialsTab'

// ── Tab Definitions ─────────────────────────────────────────────────────────────
type TabId = 'learn' | 'flashcards' | 'notes' | 'materials' | 'practice' | 'examlab' | 'reports' | 'export'

interface TabDef {
  id: TabId
  label: string
  icon: string
}

const TABS: TabDef[] = [
  { id: 'learn',      label: 'Learn',      icon: '📖' },
  { id: 'flashcards', label: 'Flashcards', icon: '🃏' },
  { id: 'notes',      label: 'Notes',      icon: '🗒️' },
  { id: 'materials',  label: 'Materials',  icon: '📚' },
  { id: 'practice',   label: 'Practice',   icon: '📝' },
  { id: 'examlab',    label: 'Exam Lab',   icon: '🧪' },
  { id: 'reports',    label: 'Reports',    icon: '📊' },
  { id: 'export',     label: 'Export',     icon: '📤' },
]

// ── Main Component ──────────────────────────────────────────────────────────────
export default function SpacePage() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const { user } = useAuth()

  const [space, setSpace] = useState<SpaceDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<TabId>('learn')

  const examId = space?.exam_id ?? searchParams.get('exam') ?? ''
  const subject = space?.subject ?? searchParams.get('subject') ?? ''
  const exam = getExamById(examId)

  useEffect(() => {
    if (!user) return

    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        if (id) {
          // /space/:id — load existing space
          const data = await spaceService.getById(Number(id))
          setSpace(data)
        } else {
          // /space/new?exam=X&subject=Y — create or retrieve space
          const examParam = searchParams.get('exam')
          const subjectParam = searchParams.get('subject')
          if (!examParam || !subjectParam) {
            navigate('/dashboard', { replace: true })
            return
          }
          const newSpace = await spaceService.createOrGet({
            exam_id: examParam,
            subject: subjectParam,
          })
          // Redirect to canonical URL with the space ID
          navigate(`/space/${newSpace.id}`, { replace: true })
          // Load full detail (with messages)
          const detail = await spaceService.getById(newSpace.id)
          setSpace(detail)
        }
      } catch (err: any) {
        setError(err?.response?.data?.detail ?? err?.message ?? 'Failed to load space.')
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [id, user, navigate, searchParams])

  // ── Loading skeleton ──────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-screen bg-surface-900 flex flex-col">
        <Navbar examName={exam?.name ?? 'Loading…'} />
        <SpaceHeaderSkeleton />
        <div className="flex-1 p-6 max-w-2xl mx-auto w-full">
          <div className="space-y-4">
            <div className="skeleton h-32 rounded-2xl" />
            <div className="skeleton h-20 rounded-2xl" />
            <div className="skeleton h-24 rounded-2xl" />
          </div>
        </div>
      </div>
    )
  }

  // ── Error ─────────────────────────────────────────────────────────────────────
  if (error) {
    return (
      <div className="min-h-screen flex flex-col" style={{ backgroundColor: 'var(--bg)' }}>
        <Navbar examName={exam?.name ?? '—'} />
        <div className="flex-1 flex items-center justify-center px-4">
          <div className="glass-card rounded-2xl p-8 text-center max-w-sm">
            <AlertCircle className="w-10 h-10 text-red-400 mx-auto mb-4" />
            <h2 className="font-display text-lg font-bold text-white mb-2">Something went wrong</h2>
            <p className="text-slate-400 text-sm mb-6">{error}</p>
            <button onClick={() => navigate('/dashboard')} className="btn-primary text-sm px-5 py-2">
              Back to Dashboard
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (!space) return null

  const subjectInfo = exam?.subjects.find((s) => s.name === space.subject)

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: 'var(--bg)' }}>
      <Navbar examName={exam?.name ?? space.exam_id} />

      <div className="relative z-10 flex flex-col flex-1" style={{ minHeight: '0' }}>

        {/* ── Header ── */}
        <div style={{ borderBottom: '1px solid var(--border)', backgroundColor: 'var(--bg-surface)' }}>
          <div className="max-w-5xl mx-auto px-4 sm:px-6 py-4">

            {/* Breadcrumb */}
            <div className="flex items-center gap-1.5 text-xs mb-3" style={{ color: 'var(--text-muted)' }}>
              <button onClick={() => navigate('/dashboard')} className="hover:text-white transition-colors">
                Dashboard
              </button>
              <ChevronRight className="w-3 h-3" />
              <span>{space.exam_id}</span>
              <ChevronRight className="w-3 h-3" />
              <span className="font-medium text-white">
                {space.subject}
              </span>
            </div>

            {/* Title row */}
            <div className="flex items-center gap-3">
              <div className={`w-10 h-10 rounded-xl ${subjectInfo?.bgClass ?? 'bg-brand-500/10'} border ${subjectInfo?.borderClass ?? 'border-brand-500/20'} flex items-center justify-center text-xl`}>
                {subjectInfo?.icon ?? '📚'}
              </div>
              <div>
                <h1 className="text-lg font-semibold text-white">{space.title}</h1>
                <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{space.exam_id} · Learning Space</p>
              </div>
            </div>

            {/* ── Tab bar ── */}
            <div className="flex gap-1 mt-4 overflow-x-auto scrollbar-hide">
              {TABS.map((tab) => {
                const isActive = activeTab === tab.id
                return (
                  <button
                    key={tab.id}
                    id={`tab-${tab.id}`}
                    onClick={() => setActiveTab(tab.id)}
                    className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 flex-shrink-0"
                    style={{
                      backgroundColor: isActive ? 'var(--accent-soft)' : 'transparent',
                      color: isActive ? 'var(--accent)' : 'var(--text-muted)',
                      border: isActive ? '1px solid rgba(90, 127, 245, 0.2)' : '1px solid transparent',
                    }}
                    onMouseEnter={(e) => {
                      if (!isActive) e.currentTarget.style.color = 'var(--text)'
                    }}
                    onMouseLeave={(e) => {
                      if (!isActive) e.currentTarget.style.color = 'var(--text-muted)'
                    }}
                  >
                    <span>{tab.icon}</span>
                    <span>{tab.label}</span>
                  </button>
                )
              })}
            </div>
          </div>
        </div>

        {/* ── Tab content ── */}
        <div className="flex-1 overflow-y-auto relative">
          {activeTab === 'learn' && (
            <LearnTab
              spaceId={space.id}
              initialMessages={space.messages}
              subject={space.subject}
              examId={space.exam_id}
            />
          )}
          {activeTab === 'flashcards' && (
            <FlashcardsTab spaceId={space.id} subject={space.subject} examId={space.exam_id} />
          )}
          {activeTab === 'notes' && (
            <NotesTab spaceId={space.id} subject={space.subject} />
          )}
          {activeTab === 'materials' && (
            <MaterialsTab spaceId={space.id} subject={space.subject} />
          )}
          {activeTab === 'practice' && (
            <PracticeTab spaceId={space.id} subject={space.subject} examId={space.exam_id} />
          )}
          {activeTab === 'examlab' && (
            <ExamLabTab spaceId={space.id} subject={space.subject} examId={space.exam_id} />
          )}
          {activeTab === 'reports' && (
            <ReportsTab spaceId={space.id} subject={space.subject} examId={space.exam_id} />
          )}
          {activeTab === 'export' && (
            <ExportTab spaceId={space.id} subject={space.subject} examId={space.exam_id} />
          )}
        </div>
      </div>
    </div>
  )
}
