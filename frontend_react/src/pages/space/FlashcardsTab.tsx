import { useState, useEffect } from 'react'
import {
  Loader2, Sparkles, Trash2, ChevronLeft, ChevronRight,
  RotateCcw, Plus, BookOpen,
} from 'lucide-react'
import { flashcardService, type Flashcard } from '../../services/flashcardService'
import { useToast } from '../../components/Toast'

interface FlashcardsTabProps {
  spaceId: number
  subject: string
  examId: string
}

type Phase = 'browse' | 'study' | 'generating'

export default function FlashcardsTab({ spaceId, subject, examId }: FlashcardsTabProps) {
  const { success: toastSuccess, error: toastError } = useToast()

  const [topics, setTopics] = useState<string[]>([])
  const [topicsLoading, setTopicsLoading] = useState(true)
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null)
  const [cards, setCards] = useState<Flashcard[]>([])
  const [cardsLoading, setCardsLoading] = useState(false)
  const [phase, setPhase] = useState<Phase>('browse')

  // Generate form
  const [newTopic, setNewTopic] = useState('')
  const [count, setCount] = useState(8)
  const [generating, setGenerating] = useState(false)

  // Study mode
  const [current, setCurrent] = useState(0)
  const [flipped, setFlipped] = useState(false)

  // Load topics on mount
  useEffect(() => {
    let cancelled = false
    setTopicsLoading(true)
    flashcardService.getTopics(spaceId)
      .then((t) => { if (!cancelled) setTopics(t) })
      .catch(() => {})
      .finally(() => { if (!cancelled) setTopicsLoading(false) })
    return () => { cancelled = true }
  }, [spaceId])

  // Load cards when topic selected
  useEffect(() => {
    if (!selectedTopic) return
    let cancelled = false
    setCardsLoading(true)
    flashcardService.list(spaceId, selectedTopic)
      .then((c) => { if (!cancelled) { setCards(c); setCurrent(0); setFlipped(false) } })
      .catch(() => {})
      .finally(() => { if (!cancelled) setCardsLoading(false) })
    return () => { cancelled = true }
  }, [spaceId, selectedTopic])

  const handleGenerate = async () => {
    if (!newTopic.trim()) return
    setGenerating(true)
    try {
      const newCards = await flashcardService.generate(spaceId, { topic: newTopic.trim(), count })
      // Refresh topics list
      const updatedTopics = await flashcardService.getTopics(spaceId)
      setTopics(updatedTopics)
      setCards(newCards)
      setSelectedTopic(newTopic.trim())
      setCurrent(0)
      setFlipped(false)
      setPhase('study')
      setNewTopic('')
      toastSuccess(`${newCards.length} flashcards generated for "${newTopic.trim()}"!`)
    } catch (e: any) {
      toastError(e?.response?.data?.detail ?? e?.message ?? 'Generation failed')
    } finally {
      setGenerating(false)
    }
  }

  const handleDeleteTopic = async (topic: string) => {
    try {
      await flashcardService.deleteTopic(spaceId, topic)
      const updated = topics.filter((t) => t !== topic)
      setTopics(updated)
      if (selectedTopic === topic) {
        setSelectedTopic(null)
        setCards([])
        setPhase('browse')
      }
      toastSuccess(`Deleted flashcards for "${topic}"`)
    } catch {
      toastError('Failed to delete flashcards')
    }
  }

  const handleStudyTopic = (topic: string) => {
    setSelectedTopic(topic)
    setPhase('study')
  }

  const next = () => { setCurrent((c) => Math.min(c + 1, cards.length - 1)); setFlipped(false) }
  const prev = () => { setCurrent((c) => Math.max(c - 1, 0)); setFlipped(false) }
  const restart = () => { setCurrent(0); setFlipped(false) }

  // ── Generate form ────────────────────────────────────────────────────────────
  const GenerateForm = () => (
    <div className="max-w-lg mx-auto">
      <h3 className="text-base font-semibold text-white mb-5 flex items-center gap-2">
        <Plus className="w-4 h-4" style={{ color: 'var(--accent)' }} />
        Generate New Flashcards
      </h3>
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1.5" htmlFor="fc-topic">
            Topic
          </label>
          <input
            id="fc-topic"
            type="text"
            value={newTopic}
            onChange={(e) => setNewTopic(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleGenerate()}
            placeholder={`e.g. Laws of Motion, Cell Division…`}
            className="input-field"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-1.5" htmlFor="fc-count">
            Number of cards
          </label>
          <select
            id="fc-count"
            value={count}
            onChange={(e) => setCount(Number(e.target.value))}
            className="input-field"
          >
            {[5, 8, 10, 15, 20].map((n) => (
              <option key={n} value={n}>{n} cards</option>
            ))}
          </select>
        </div>
        <button
          id="generate-flashcards-btn"
          onClick={handleGenerate}
          disabled={!newTopic.trim() || generating}
          className="btn-primary w-full justify-center disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {generating ? (
            <><Loader2 className="w-4 h-4 animate-spin" /> Generating…</>
          ) : (
            <><Sparkles className="w-4 h-4" /> Generate Flashcards</>
          )}
        </button>
      </div>
    </div>
  )

  // ── Study mode ───────────────────────────────────────────────────────────────
  if (phase === 'study' && selectedTopic) {
    if (cardsLoading) {
      return (
        <div className="flex items-center justify-center py-24">
          <Loader2 className="w-6 h-6 text-brand-400 animate-spin" />
        </div>
      )
    }

    const card = cards[current]
    const isLast = current === cards.length - 1
    const isFirst = current === 0

    return (
      <div className="max-w-2xl mx-auto px-4 py-8 tab-panel-enter">
        {/* Back button + info */}
        <div className="flex items-center justify-between mb-6">
          <button
            onClick={() => { setPhase('browse'); setFlipped(false) }}
            className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-white transition-colors"
          >
            <ChevronLeft className="w-4 h-4" />
            All Topics
          </button>
          <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
            <span className="font-medium" style={{ color: 'var(--text)' }}>{selectedTopic}</span>
            {' · '}Card {current + 1} of {cards.length}
          </div>
          <button
            onClick={restart}
            className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Restart
          </button>
        </div>

        {/* Progress bar */}
        <div className="w-full h-1.5 rounded-full mb-8" style={{ backgroundColor: 'var(--border-soft)' }}>
          <div
            className="h-1.5 rounded-full transition-all duration-300"
            style={{ width: `${((current + 1) / cards.length) * 100}%`, backgroundColor: 'var(--accent)' }}
          />
        </div>

        {/* ── Flip Card ── */}
        <div
          className="relative w-full cursor-pointer select-none mb-8"
          style={{ perspective: '1200px', minHeight: '280px' }}
          onClick={() => setFlipped((f) => !f)}
          id="flashcard-flip"
        >
          <div
            className="relative w-full transition-all duration-500"
            style={{
              transformStyle: 'preserve-3d',
              transform: flipped ? 'rotateY(180deg)' : 'rotateY(0deg)',
              minHeight: '280px',
            }}
          >
            {/* Front */}
            <div
              className="absolute inset-0 glass-card rounded-2xl p-8 flex flex-col items-center justify-center text-center"
              style={{ backfaceVisibility: 'hidden' }}
            >
              <div className="text-xs font-medium uppercase tracking-widest mb-4" style={{ color: 'var(--accent)' }}>
                Question / Term
              </div>
              <p className="text-white text-lg font-semibold leading-relaxed">{card?.front}</p>
              <p className="text-xs mt-6 flex items-center gap-1.5" style={{ color: 'var(--text-dim)' }}>
                <RotateCcw className="w-3 h-3" />
                Tap to reveal answer
              </p>
            </div>

            {/* Back */}
            <div
              className="absolute inset-0 rounded-2xl p-8 flex flex-col items-center justify-center text-center"
              style={{
                backfaceVisibility: 'hidden',
                transform: 'rotateY(180deg)',
                backgroundColor: 'var(--bg-elevated)',
                border: '1px solid var(--border)',
              }}
            >
              <div className="text-xs font-medium uppercase tracking-widest mb-4" style={{ color: 'var(--green)' }}>
                Answer / Definition
              </div>
              <p className="text-white text-base leading-relaxed">{card?.back}</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <div className="flex items-center justify-center gap-4">
          <button
            id="fc-prev-btn"
            onClick={prev}
            disabled={isFirst}
            className="btn-outline py-2 px-5 text-sm disabled:opacity-30"
          >
            <ChevronLeft className="w-4 h-4" />
            Prev
          </button>
          {isLast ? (
            <button
              id="fc-finish-btn"
              onClick={restart}
              className="btn-primary py-2 px-6 text-sm"
            >
              <RotateCcw className="w-4 h-4" />
              Review Again
            </button>
          ) : (
            <button
              id="fc-next-btn"
              onClick={next}
              className="btn-primary py-2 px-6 text-sm"
            >
              Next
              <ChevronRight className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    )
  }

  // ── Browse / manage ──────────────────────────────────────────────────────────
  return (
    <div className="max-w-2xl mx-auto px-4 py-8 tab-panel-enter">
      <div className="grid md:grid-cols-2 gap-8">

        {/* Left: Existing topics */}
        <div>
          <h3 className="text-base font-semibold text-white mb-4 flex items-center gap-2">
            <BookOpen className="w-4 h-4" style={{ color: 'var(--accent)' }} />
            Your Flashcard Sets
          </h3>

          {topicsLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <div key={i} className="skeleton h-14 rounded-xl" />
              ))}
            </div>
          ) : topics.length === 0 ? (
            <div className="glass-card rounded-xl p-6 text-center">
              <p className="text-slate-500 text-sm">No flashcard sets yet.</p>
              <p className="text-slate-600 text-xs mt-1">Generate your first set →</p>
            </div>
          ) : (
            <div className="space-y-2">
              {topics.map((topic) => (
                <div
                  key={topic}
                  className="group glass-card rounded-xl px-4 py-3 flex items-center gap-3 hover:border-brand-500/30 transition-all"
                >
                  <button
                    className="flex-1 text-left"
                    onClick={() => handleStudyTopic(topic)}
                    id={`study-${topic.replace(/\s+/g, '-')}`}
                  >
                    <p className="text-sm font-medium text-white group-hover:text-white transition-colors">
                      {topic}
                    </p>
                    <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{examId} · {subject}</p>
                  </button>
                  <button
                    onClick={() => handleStudyTopic(topic)}
                    className="text-xs font-medium transition-colors whitespace-nowrap"
                    style={{ color: 'var(--accent)' }}
                  >
                    Study →
                  </button>
                  <button
                    onClick={() => handleDeleteTopic(topic)}
                    className="opacity-0 group-hover:opacity-100 text-slate-600 hover:text-red-400 transition-all"
                    title="Delete this set"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right: Generate new */}
        <div>
          <GenerateForm />
        </div>
      </div>
    </div>
  )
}
