import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, CheckCircle2, Loader2 } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { examService } from '../services/examService'
import { EXAMS, ExamInfo } from '../constants/exams'
import Navbar from '../components/Navbar'

export default function SelectExam() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const [selected, setSelected] = useState<string | null>(user?.selected_exam ?? null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSelect = (examId: string) => {
    setSelected(examId)
    setError(null)
  }

  const handleConfirm = async () => {
    if (!selected) {
      setError('Please select an exam to continue.')
      return
    }
    setLoading(true)
    try {
      await examService.selectExam(selected)
      // Update the cached user object
      const raw = localStorage.getItem('vinaval_user')
      if (raw) {
        const u = JSON.parse(raw)
        u.selected_exam = selected
        localStorage.setItem('vinaval_user', JSON.stringify(u))
      }
      navigate('/dashboard')
    } catch {
      setError('Failed to save selection. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-surface-900">
      {/* Orbs */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="orb w-[500px] h-[500px] bg-brand-700 top-[-100px] right-[-100px]" />
        <div className="orb w-[400px] h-[400px] bg-purple-800 bottom-[-100px] left-[-100px]" />
      </div>

      <Navbar />

      <main className="relative z-10 max-w-4xl mx-auto px-4 pt-16 pb-24">
        {/* Header */}
        <div className="text-center mb-14">
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full glass-card border-brand-500/20 mb-6">
            <span className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-pulse" />
            <span className="text-xs text-brand-300 font-medium tracking-wide uppercase">Step 1 of 1</span>
          </div>
          <h1 className="font-display text-4xl md:text-5xl font-extrabold mb-4">
            Choose Your <span className="gradient-text">Exam Track</span>
          </h1>
          <p className="text-slate-400 text-lg max-w-xl mx-auto">
            Your workspace, practice questions, and AI answers will all be tailored to your chosen examination.
          </p>
        </div>

        {/* Exam Cards */}
        <div className="grid md:grid-cols-2 gap-6 mb-10">
          {EXAMS.map((exam: ExamInfo) => {
            const isSelected = selected === exam.id
            return (
              <button
                key={exam.id}
                id={`exam-card-${exam.id.toLowerCase()}`}
                onClick={() => handleSelect(exam.id)}
                className={`
                  relative text-left rounded-2xl p-6 border transition-all duration-300
                  ${isSelected
                    ? 'border-brand-500/60 bg-brand-500/10 shadow-xl shadow-brand-500/20 scale-[1.02]'
                    : 'glass-card hover:border-brand-500/30 hover:-translate-y-1'
                  }
                `}
              >
                {/* Selected check */}
                {isSelected && (
                  <div className="absolute top-4 right-4">
                    <CheckCircle2 className="w-6 h-6 text-brand-400" />
                  </div>
                )}

                {/* Card header */}
                <div className="mb-5">
                  <div className="inline-flex items-center gap-2 mb-3">
                    <span className="font-display text-3xl font-extrabold gradient-text">{exam.name}</span>
                    <span className="px-2.5 py-1 rounded-full text-xs font-medium bg-white/5 text-slate-400 border border-white/10">
                      {exam.tag}
                    </span>
                  </div>
                  <p className="text-slate-400 text-sm leading-relaxed">{exam.description}</p>
                </div>

                {/* Subjects */}
                <div className="space-y-2">
                  <p className="text-xs text-slate-500 uppercase tracking-widest font-medium mb-3">Subjects Covered</p>
                  <div className="flex flex-wrap gap-2">
                    {exam.subjects.map(sub => (
                      <span
                        key={sub.name}
                        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border ${sub.bgClass} ${sub.textClass} ${sub.borderClass}`}
                      >
                        <span>{sub.icon}</span>
                        {sub.name}
                      </span>
                    ))}
                  </div>
                </div>
              </button>
            )
          })}
        </div>

        {/* Error */}
        {error && (
          <p className="text-center text-rose-400 text-sm mb-6 bg-rose-500/10 border border-rose-500/20 rounded-xl py-3 px-4">
            {error}
          </p>
        )}

        {/* CTA */}
        <div className="flex justify-center">
          <button
            id="confirm-exam-btn"
            onClick={handleConfirm}
            disabled={!selected || loading}
            className="btn-primary px-10 py-4 text-base rounded-2xl disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
          >
            {loading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : null}
            {loading ? 'Saving…' : 'Enter Dashboard'}
            {!loading && <ArrowRight className="w-5 h-5" />}
          </button>
        </div>
        <p className="text-center text-slate-600 text-xs mt-4">
          You can switch exams anytime from the navigation bar.
        </p>
      </main>
    </div>
  )
}
