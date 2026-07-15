import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import {
  Brain, BookOpen, FlaskConical, BarChart3, StickyNote,
  Layers, ArrowRight, CheckCircle2, Shield, Loader2,
} from 'lucide-react'

const FEATURES = [
  { icon: BookOpen,     title: 'AI-Powered Learning',   desc: 'Ask anything about your syllabus. Get grounded answers from Tamil Nadu State Board textbooks — never hallucinated.' },
  { icon: FlaskConical, title: 'Smart Practice Tests',  desc: 'Generate adaptive MCQs tailored to any topic, with instant feedback and explanations.' },
  { icon: Brain,        title: 'Exam Lab',              desc: 'Simulate a timed exam with up to 30 questions. Track your score and review answers at the end.' },
  { icon: BarChart3,    title: 'Progress Reports',      desc: 'Visual accuracy rings and topic-wise breakdown of your practice and exam performance.' },
  { icon: StickyNote,   title: 'Personal Notes',        desc: 'Markdown-aware notes auto-saved to your Learning Space. Export as .md or .txt anytime.' },
  { icon: Layers,       title: 'Flashcards',            desc: 'AI-generated flip cards. Study a topic, flip to check the answer, and restart to review.' },
]

const EXAMS = [
  { name: 'NEET',  tag: 'Medical Entrance', subjects: ['Physics', 'Chemistry', 'Botany', 'Zoology'] },
  { name: 'TNPSC', tag: 'Civil Services',   subjects: ['History', 'Geography', 'Polity', 'Economics', 'Science', 'Current Affairs'] },
]

const STEPS = [
  { step: '01', title: 'Sign in with Google',     desc: 'One-click sign-in. Your data stays private and secure.' },
  { step: '02', title: 'Select Your Exam',         desc: 'Choose NEET or TNPSC. Your workspace adapts to your exam.' },
  { step: '03', title: 'Open a Learning Space',    desc: 'Pick any subject to open a dedicated study environment.' },
  { step: '04', title: 'Learn, Practice & Revise', desc: 'Use all 7 modules — AI chat, flashcards, practice, exam lab, reports, notes, and export.' },
]

export default function LandingPage() {
  const navigate = useNavigate()
  const { isAuthenticated, signInWithGoogle } = useAuth()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (isAuthenticated) navigate('/select-exam', { replace: true })
  }, [isAuthenticated])

  const handleGoogleLogin = async () => {
    setIsLoading(true)
    setError(null)
    try {
      await signInWithGoogle()
    } catch (err: any) {
      if (err?.code !== 'auth/popup-closed-by-user') {
        setError('Sign-in failed. Please try again.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen text-white" style={{ backgroundColor: 'var(--bg)' }}>

      {/* ── Navbar ─────────────────────────────────── */}
      <nav style={{ borderBottom: '1px solid var(--border)' }}>
        <div className="max-w-5xl mx-auto px-5 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Brain className="w-5 h-5" style={{ color: 'var(--accent)' }} />
            <span className="font-semibold text-white text-base">Vinaval AI</span>
          </div>
          <button
            id="nav-signin-btn"
            onClick={handleGoogleLogin}
            disabled={isLoading}
            className="btn-outline text-sm disabled:opacity-60"
          >
            {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Sign in with Google'}
          </button>
        </div>
      </nav>

      {/* ── Hero ────────────────────────────────────── */}
      <section className="max-w-2xl mx-auto px-5 pt-20 pb-16 text-center">
        <div className="tag mb-6 mx-auto w-fit">
          <span className="glow-dot" />
          AI-Powered · RAG-Grounded · Tamil Nadu Syllabus
        </div>

        <h1 className="text-4xl md:text-5xl font-bold leading-tight mb-5 text-white">
          Your Study Partner for<br />
          <span style={{ color: 'var(--accent)' }}>NEET &amp; TNPSC</span>
        </h1>

        <p className="mb-8 text-base leading-relaxed" style={{ color: 'var(--text-muted)' }}>
          Learn with AI answers grounded in State Board textbooks.
          Practice smarter with adaptive MCQs. Revise with AI-generated flashcards.
        </p>

        <button
          id="hero-signin-btn"
          onClick={handleGoogleLogin}
          disabled={isLoading}
          className="btn-primary text-sm mx-auto disabled:opacity-70"
        >
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <GoogleIcon />
          )}
          {isLoading ? 'Signing in…' : 'Continue with Google'}
          {!isLoading && <ArrowRight className="w-4 h-4" />}
        </button>

        <p className="mt-3 text-xs" style={{ color: 'var(--text-dim)' }}>
          Free to use · No credit card required
        </p>

        {error && (
          <div className="mt-4 text-sm px-4 py-2 rounded-lg border inline-block"
               style={{ color: 'var(--red)', borderColor: 'var(--red-soft)', backgroundColor: 'var(--red-soft)' }}>
            {error}
          </div>
        )}

        {/* Stats */}
        <div className="mt-14 grid grid-cols-4 gap-3">
          {[
            { v: '7', l: 'Modules' },
            { v: '2', l: 'Exam Tracks' },
            { v: 'RAG', l: 'AI Engine' },
            { v: '100%', l: 'Grounded' },
          ].map((s) => (
            <div key={s.l} className="glass-card rounded-xl p-4 text-center">
              <div className="text-2xl font-bold mb-1" style={{ color: 'var(--accent)' }}>{s.v}</div>
              <div className="text-xs" style={{ color: 'var(--text-dim)' }}>{s.l}</div>
            </div>
          ))}
        </div>
      </section>

      <hr className="divider max-w-5xl mx-auto" />

      {/* ── Exam Tracks ─────────────────────────────── */}
      <section className="max-w-5xl mx-auto px-5 py-16">
        <h2 className="text-xl font-semibold text-white mb-2">Exam Tracks</h2>
        <p className="text-sm mb-8" style={{ color: 'var(--text-muted)' }}>
          Separate learning workspaces for each exam. Switch any time.
        </p>
        <div className="grid md:grid-cols-2 gap-4">
          {EXAMS.map((exam) => (
            <div key={exam.name} className="glass-card rounded-xl p-5">
              <div className="flex items-start justify-between mb-3">
                <div>
                  <div className="font-semibold text-white text-lg">{exam.name}</div>
                  <div className="text-xs mt-0.5" style={{ color: 'var(--text-dim)' }}>{exam.tag}</div>
                </div>
              </div>
              <div className="flex flex-wrap gap-2">
                {exam.subjects.map((sub) => (
                  <span key={sub} className="tag">{sub}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      <hr className="divider max-w-5xl mx-auto" />

      {/* ── Features ──────────────────────────────────── */}
      <section className="max-w-5xl mx-auto px-5 py-16">
        <h2 className="text-xl font-semibold text-white mb-2">Everything in one space</h2>
        <p className="text-sm mb-8" style={{ color: 'var(--text-muted)' }}>
          7 purpose-built modules. Every module shares your learning data.
        </p>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {FEATURES.map((f) => (
            <div key={f.title} className="feature-card rounded-xl">
              <div className="w-9 h-9 rounded-lg flex items-center justify-center mb-4"
                   style={{ backgroundColor: 'var(--accent-soft)', border: '1px solid rgba(90,127,245,0.2)' }}>
                <f.icon className="w-4 h-4" style={{ color: 'var(--accent)' }} />
              </div>
              <h3 className="font-medium text-white mb-1.5">{f.title}</h3>
              <p className="text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <hr className="divider max-w-5xl mx-auto" />

      {/* ── How It Works ──────────────────────────────── */}
      <section className="max-w-3xl mx-auto px-5 py-16">
        <h2 className="text-xl font-semibold text-white mb-2">How it works</h2>
        <p className="text-sm mb-8" style={{ color: 'var(--text-muted)' }}>Four simple steps to get started.</p>
        <div className="space-y-3">
          {STEPS.map((item) => (
            <div key={item.step} className="glass-card rounded-xl p-4 flex items-start gap-4">
              <div className="w-9 h-9 rounded-lg flex-shrink-0 flex items-center justify-center text-sm font-semibold"
                   style={{ backgroundColor: 'var(--accent-soft)', border: '1px solid rgba(90,127,245,0.25)', color: 'var(--accent)' }}>
                {item.step}
              </div>
              <div>
                <div className="font-medium text-white text-sm mb-0.5">{item.title}</div>
                <div className="text-sm" style={{ color: 'var(--text-muted)' }}>{item.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <hr className="divider max-w-5xl mx-auto" />

      {/* ── Trust ─────────────────────────────────────── */}
      <section className="max-w-3xl mx-auto px-5 py-16">
        <div className="glass-card rounded-xl p-6">
          <div className="flex items-center gap-2 mb-3">
            <Shield className="w-4 h-4" style={{ color: 'var(--accent)' }} />
            <h3 className="font-semibold text-white">Built for accuracy, not impressiveness</h3>
          </div>
          <p className="text-sm mb-5 leading-relaxed" style={{ color: 'var(--text-muted)' }}>
            Every AI answer is grounded in indexed Tamil Nadu State Board textbooks using
            Retrieval-Augmented Generation (RAG). If the answer isn't in the books, Vinaval AI
            will say so — never hallucinate.
          </p>
          <div className="flex flex-wrap gap-2">
            {['State Board Textbooks', 'RAG (Not Hallucination)', 'Subject Isolation', 'Groq LLM'].map((tag) => (
              <span key={tag} className="flex items-center gap-1.5 tag">
                <CheckCircle2 className="w-3 h-3" style={{ color: 'var(--green)' }} />
                {tag}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── Final CTA ─────────────────────────────────── */}
      <section className="max-w-xl mx-auto px-5 py-16 text-center">
        <h2 className="text-2xl font-semibold text-white mb-3">Ready to study smarter?</h2>
        <p className="text-sm mb-7" style={{ color: 'var(--text-muted)' }}>
          Join Tamil Nadu aspirants learning with AI that knows your syllabus.
        </p>
        <button
          id="footer-signin-btn"
          onClick={handleGoogleLogin}
          className="btn-primary mx-auto"
        >
          <GoogleIcon />
          Get Started — It's Free
          <ArrowRight className="w-4 h-4" />
        </button>
      </section>

      {/* ── Footer ────────────────────────────────────── */}
      <footer style={{ borderTop: '1px solid var(--border-soft)' }}>
        <div className="max-w-5xl mx-auto px-5 py-6 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Brain className="w-4 h-4" style={{ color: 'var(--accent)' }} />
            <span className="font-semibold text-white text-sm">Vinaval AI</span>
          </div>
          <p className="text-xs" style={{ color: 'var(--text-dim)' }}>
            © 2026 Vinaval AI · AI Learning Arena for Tamil Nadu Aspirants
          </p>
        </div>
      </footer>
    </div>
  )
}

function GoogleIcon() {
  return (
    <svg className="w-4 h-4 flex-shrink-0" viewBox="0 0 24 24" fill="none">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="currentColor" opacity="0.9"/>
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="currentColor" opacity="0.8"/>
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="currentColor" opacity="0.7"/>
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="currentColor" opacity="0.85"/>
    </svg>
  )
}
