import { useState, useRef } from 'react'
import { Loader2, ChevronRight, RotateCcw, CheckCircle, XCircle } from 'lucide-react'
import { quizService } from '../../services/quizService'
import type { QuizQuestion, AnswerResult } from '../../types/quiz'

interface PracticeTabProps {
  spaceId: number
  subject: string
  examId: string
}

type Phase = 'setup' | 'quiz' | 'done'

const OPTION_KEYS = ['a', 'b', 'c', 'd'] as const
type OptionKey = typeof OPTION_KEYS[number]

export default function PracticeTab({ spaceId, subject, examId }: PracticeTabProps) {
  const [topic, setTopic] = useState('')
  const [count, setCount] = useState(5)
  const [phase, setPhase] = useState<Phase>('setup')
  const [questions, setQuestions] = useState<QuizQuestion[]>([])
  const [current, setCurrent] = useState(0)
  const [selected, setSelected] = useState<OptionKey | null>(null)
  const [result, setResult] = useState<AnswerResult | null>(null)
  const [score, setScore] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const startTimeRef = useRef<number>(0)

  const q = questions[current]

  const handleGenerate = async () => {
    if (!topic.trim()) return
    setLoading(true)
    setError(null)
    try {
      const qs = await quizService.generate(spaceId, { topic: topic.trim(), count })
      setQuestions(qs)
      setCurrent(0)
      setScore(0)
      setSelected(null)
      setResult(null)
      setPhase('quiz')
      startTimeRef.current = Date.now()
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? 'Failed to generate questions')
    } finally {
      setLoading(false)
    }
  }

  const handleSelect = async (option: OptionKey) => {
    if (selected !== null || !q) return
    setSelected(option)
    const timeTaken = Math.round((Date.now() - startTimeRef.current) / 1000)
    try {
      const res = await quizService.submitAnswer(spaceId, {
        question_id: q.id,
        user_answer: option,
        time_taken_seconds: timeTaken,
        is_exam: false,
      })
      setResult(res)
      if (res.is_correct) setScore((s) => s + 1)
    } catch {
      setResult(null)
    }
  }

  const handleNext = () => {
    if (current + 1 >= questions.length) {
      setPhase('done')
    } else {
      setCurrent((c) => c + 1)
      setSelected(null)
      setResult(null)
      startTimeRef.current = Date.now()
    }
  }

  const handleRestart = () => {
    setPhase('setup')
    setTopic('')
    setQuestions([])
    setSelected(null)
    setResult(null)
    setScore(0)
  }

  // ── Setup screen ──────────────────────────────────────────────────────────
  if (phase === 'setup') {
    return (
      <div className="max-w-lg mx-auto px-4 py-12">
        <h2 className="text-lg font-semibold text-white mb-1">Practice Questions</h2>
        <p className="text-slate-400 text-sm mb-8">
          Enter a topic from {examId} {subject} and generate MCQs to test yourself.
        </p>

        <div className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5" htmlFor="topic-input">
              Topic
            </label>
            <input
              id="topic-input"
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleGenerate()}
              placeholder={`e.g. Newton's Laws, Photosynthesis…`}
              className="input-field"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1.5" htmlFor="count-select">
              Number of questions
            </label>
            <select
              id="count-select"
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
              className="input-field"
            >
              {[3, 5, 7, 10].map((n) => (
                <option key={n} value={n}>{n} questions</option>
              ))}
            </select>
          </div>

          {error && (
            <p className="text-red-400 text-sm">{error}</p>
          )}

          <button
            id="generate-btn"
            onClick={handleGenerate}
            disabled={!topic.trim() || loading}
            className="btn-primary w-full justify-center disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? (
              <><Loader2 className="w-4 h-4 animate-spin" /> Generating…</>
            ) : (
              <>Generate Questions <ChevronRight className="w-4 h-4" /></>
            )}
          </button>
        </div>
      </div>
    )
  }

  // ── Done screen ───────────────────────────────────────────────────────────
  if (phase === 'done') {
    const pct = Math.round((score / questions.length) * 100)
    return (
      <div className="max-w-sm mx-auto px-4 py-12 text-center">
        <div className="text-5xl mb-4">{pct >= 70 ? '🎉' : pct >= 40 ? '📚' : '💪'}</div>
        <h2 className="text-xl font-bold text-white mb-1">Session Complete!</h2>
        <p className="text-slate-400 text-sm mb-6">Topic: {questions[0]?.topic}</p>

        <div className="glass-card rounded-2xl p-6 mb-6">
          <div className="text-4xl font-bold text-white mb-1">{score}/{questions.length}</div>
          <div className="text-slate-400 text-sm">{pct}% accuracy</div>
        </div>

        <button id="restart-btn" onClick={handleRestart} className="btn-outline w-full justify-center">
          <RotateCcw className="w-4 h-4" /> Practice Again
        </button>
      </div>
    )
  }

  // ── Quiz screen ───────────────────────────────────────────────────────────
  if (!q) return null

  const optionLabels: Record<OptionKey, string> = {
    a: q.option_a,
    b: q.option_b,
    c: q.option_c,
    d: q.option_d,
  }

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      {/* Progress */}
      <div className="flex items-center justify-between mb-6">
        <span className="text-slate-400 text-sm">
          Question {current + 1} of {questions.length}
        </span>
        <span className="text-slate-400 text-sm">Score: {score}</span>
      </div>
      <div className="w-full h-1.5 rounded-full mb-8" style={{ backgroundColor: 'var(--border-soft)' }}>
        <div
          className="h-1.5 rounded-full transition-all duration-300"
          style={{ width: `${((current + 1) / questions.length) * 100}%`, backgroundColor: 'var(--accent)' }}
        />
      </div>

      {/* Question */}
      <div className="rounded-2xl p-6 mb-6" style={{ backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
        <p className="text-xs font-medium uppercase tracking-wide mb-3" style={{ color: 'var(--accent)' }}>{q.topic}</p>
        <p className="text-white text-base leading-relaxed">{q.question}</p>
      </div>

      {/* Options */}
      <div className="space-y-3 mb-6">
        {OPTION_KEYS.map((opt) => {
          let style = 'text-slate-200 hover:text-white transition-colors'
          let bgColor = 'var(--bg-elevated)'
          let borderColor = 'var(--border)'

          if (selected !== null) {
            if (opt === result?.correct_option) {
              style = 'text-emerald-300'
              bgColor = 'var(--green-soft)'
              borderColor = 'var(--green)'
            } else if (opt === selected && !result?.is_correct) {
              style = 'text-red-300'
              bgColor = 'var(--red-soft)'
              borderColor = 'var(--red)'
            } else {
              style = 'text-slate-500 cursor-default'
              bgColor = 'transparent'
              borderColor = 'transparent'
            }
          }

          return (
            <button
              key={opt}
              id={`option-${opt}`}
              onClick={() => handleSelect(opt)}
              disabled={selected !== null}
              className={`w-full text-left px-4 py-3 rounded-xl border text-sm transition-all duration-150 flex items-center gap-3 ${style} disabled:cursor-default`}
              style={{ backgroundColor: bgColor, borderColor: borderColor }}
            >
              <span className="w-6 h-6 rounded-full border border-current flex items-center justify-center text-xs font-bold flex-shrink-0 uppercase">
                {opt}
              </span>
              <span>{optionLabels[opt]}</span>
              {selected !== null && opt === result?.correct_option && (
                <CheckCircle className="w-4 h-4 text-emerald-400 ml-auto flex-shrink-0" />
              )}
              {selected !== null && opt === selected && !result?.is_correct && (
                <XCircle className="w-4 h-4 text-red-400 ml-auto flex-shrink-0" />
              )}
            </button>
          )
        })}
      </div>

      {/* Explanation */}
      {result && result.explanation && (
        <div className={`rounded-xl p-4 mb-6 text-sm leading-relaxed ${
          result.is_correct ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-200' : 'bg-slate-800/60 border border-white/10 text-slate-300'
        }`}>
          <span className="font-medium text-white">Explanation: </span>
          {result.explanation}
        </div>
      )}

      {/* Next */}
      {selected !== null && (
        <button id="next-btn" onClick={handleNext} className="btn-primary w-full justify-center">
          {current + 1 >= questions.length ? 'See Results' : 'Next Question'}
          <ChevronRight className="w-4 h-4" />
        </button>
      )}
    </div>
  )
}
