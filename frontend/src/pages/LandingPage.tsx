import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import {
  Brain,
  BookOpen,
  FlaskConical,
  BarChart3,
  StickyNote,
  Sparkles,
  ArrowRight,
  CheckCircle2,
  Zap,
  Shield,
  Loader2,
} from 'lucide-react'

const FEATURES = [
  {
    icon: BookOpen,
    title: 'AI-Powered Learning',
    desc: 'Ask anything about your syllabus. Get grounded answers from Tamil Nadu State Board textbooks — never hallucinated.',
    color: 'text-blue-400',
    bg: 'bg-blue-500/10',
  },
  {
    icon: FlaskConical,
    title: 'Smart Practice Tests',
    desc: 'Generate adaptive MCQs, fill-in-the-blanks, and short answers tailored to your weak areas.',
    color: 'text-purple-400',
    bg: 'bg-purple-500/10',
  },
  {
    icon: Brain,
    title: 'Exam Lab',
    desc: 'Upload previous year papers. Let AI analyze topic distribution, difficulty, and map questions to chapters.',
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/10',
  },
  {
    icon: BarChart3,
    title: 'Progress Analytics',
    desc: 'Visual reports on your performance. Smart revision plans built from your actual weak areas.',
    color: 'text-amber-400',
    bg: 'bg-amber-500/10',
  },
  {
    icon: StickyNote,
    title: 'Personal Notes',
    desc: 'Rich text notes tied to your Learning Space. Pin, search, and organize your study material.',
    color: 'text-rose-400',
    bg: 'bg-rose-500/10',
  },
  {
    icon: Sparkles,
    title: 'Smart Revision',
    desc: 'AI analyzes your history and generates today\'s revision plan with priority topics and study time estimates.',
    color: 'text-cyan-400',
    bg: 'bg-cyan-500/10',
  },
]

const EXAMS = [
  { name: 'NEET', tag: 'Medical Entrance', subjects: ['Physics', 'Chemistry', 'Botany', 'Zoology'] },
  { name: 'TNPSC', tag: 'Civil Services', subjects: ['History', 'Geography', 'Polity', 'Economics', 'Science', 'Current Affairs'] },
]

const STATS = [
  { value: '6', label: 'Learning Modules' },
  { value: '2', label: 'Exam Tracks' },
  { value: '100%', label: 'Syllabus Grounded' },
  { value: 'RAG', label: 'Powered AI' },
]

export default function LandingPage() {
  const navigate = useNavigate()
  const { isAuthenticated, signInWithGoogle } = useAuth()
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/select-exam', { replace: true })
    }
  }, [isAuthenticated])

  const handleGoogleLogin = async () => {
    setIsLoading(true)
    setError(null)
    try {
      await signInWithGoogle()
    } catch (err: any) {
      // User closed popup — don't show an error
      if (err?.code !== 'auth/popup-closed-by-user') {
        setError('Sign-in failed. Please try again.')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-hero text-white overflow-x-hidden">

      {/* ── Background Orbs ──────────────────────── */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="orb w-[600px] h-[600px] bg-brand-600 top-[-200px] left-[-200px]" />
        <div className="orb w-[500px] h-[500px] bg-purple-600 top-[30%] right-[-150px]" />
        <div className="orb w-[400px] h-[400px] bg-brand-700 bottom-[-100px] left-[30%]" />
      </div>

      {/* ── Navbar ───────────────────────────────── */}
      <nav className="relative z-10 flex items-center justify-between px-6 py-5 max-w-7xl mx-auto">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-brand flex items-center justify-center shadow-lg shadow-brand-500/30">
            <Brain className="w-5 h-5 text-white" />
          </div>
          <div>
            <span className="font-display font-bold text-lg text-white">Vinaval</span>
            <span className="font-display font-bold text-lg gradient-text"> AI</span>
          </div>
        </div>
        <button
          id="nav-signin-btn"
          onClick={handleGoogleLogin}
          disabled={isLoading}
          className="btn-outline text-sm py-2 px-5 disabled:opacity-60 disabled:cursor-not-allowed"
        >
          {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Sign in with Google'}
        </button>
      </nav>

      {/* ── Hero Section ─────────────────────────── */}
      <section className="relative z-10 text-center px-6 pt-20 pb-32 max-w-5xl mx-auto">
        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass-card border-brand-500/20 mb-8 animate-fade-up">
          <div className="glow-dot animate-pulse-slow" />
          <span className="text-xs text-brand-300 font-medium tracking-wide uppercase">
            AI-Powered · RAG-Grounded · Tamil Nadu Syllabus
          </span>
        </div>

        {/* Headline */}
        <h1 className="font-display text-5xl md:text-7xl font-extrabold leading-tight mb-6 animate-fade-up">
          Your Personal{' '}
          <span className="gradient-text">AI Learning Arena</span>
          <br />
          for Tamil Nadu Aspirants
        </h1>

        {/* Subheadline */}
        <p className="text-slate-400 text-xl md:text-2xl max-w-3xl mx-auto mb-12 animate-fade-up leading-relaxed">
          Designed for <strong className="text-white">NEET</strong> and{' '}
          <strong className="text-white">TNPSC</strong> students. Learn with AI answers grounded in
          State Board textbooks. Practice smarter. Revise strategically.
        </p>

        {/* CTA */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 animate-fade-up">
          <button
            id="hero-signin-btn"
            onClick={handleGoogleLogin}
            disabled={isLoading}
            className="btn-primary text-base px-8 py-4 rounded-2xl disabled:opacity-70 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#fff"/>
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#fff" opacity="0.85"/>
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l3.66-2.84z" fill="#fff" opacity="0.7"/>
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#fff" opacity="0.9"/>
              </svg>
            )}
            {isLoading ? 'Signing in…' : 'Continue with Google'}
            {!isLoading && <ArrowRight className="w-5 h-5" />}
          </button>
          <span className="text-slate-500 text-sm">Free to use · No credit card required</span>
        </div>

        {/* Error message */}
        {error && (
          <div className="mt-4 text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-2 inline-block">
            {error}
          </div>
        )}

        {/* Stats strip */}
        <div className="mt-20 grid grid-cols-2 md:grid-cols-4 gap-4 max-w-3xl mx-auto animate-fade-up">
          {STATS.map((s) => (
            <div key={s.label} className="glass-card rounded-2xl p-4 text-center">
              <div className="font-display text-3xl font-bold gradient-text mb-1">{s.value}</div>
              <div className="text-xs text-slate-500 uppercase tracking-wide">{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Exam Tracks ──────────────────────────── */}
      <section className="relative z-10 px-6 py-20 max-w-5xl mx-auto">
        <div className="text-center mb-14">
          <h2 className="font-display text-3xl md:text-4xl font-bold mb-3">
            Choose Your <span className="gradient-text">Exam Track</span>
          </h2>
          <p className="text-slate-400">Separate learning workspaces for each examination</p>
        </div>

        <div className="grid md:grid-cols-2 gap-6">
          {EXAMS.map((exam) => (
            <div key={exam.name} className="feature-card gradient-border">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <div className="font-display text-2xl font-bold gradient-text mb-1">{exam.name}</div>
                  <div className="text-slate-500 text-sm">{exam.tag}</div>
                </div>
                <Zap className="w-5 h-5 text-brand-400 mt-1" />
              </div>
              <div className="flex flex-wrap gap-2">
                {exam.subjects.map((sub) => (
                  <span
                    key={sub}
                    className="px-3 py-1 rounded-full text-xs font-medium bg-brand-500/15 text-brand-300 border border-brand-500/20"
                  >
                    {sub}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Features Grid ────────────────────────── */}
      <section className="relative z-10 px-6 py-20 max-w-7xl mx-auto">
        <div className="text-center mb-14">
          <h2 className="font-display text-3xl md:text-4xl font-bold mb-3">
            Everything in One <span className="gradient-text">Learning Workspace</span>
          </h2>
          <p className="text-slate-400 max-w-2xl mx-auto">
            Six purpose-built modules. Every module shares your learning data for a truly personalized experience.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-5">
          {FEATURES.map((f) => (
            <div key={f.title} className="feature-card group">
              <div className={`w-11 h-11 rounded-xl ${f.bg} flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300`}>
                <f.icon className={`w-5 h-5 ${f.color}`} />
              </div>
              <h3 className="font-semibold text-white text-lg mb-2">{f.title}</h3>
              <p className="text-slate-400 text-sm leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── How It Works ─────────────────────────── */}
      <section className="relative z-10 px-6 py-20 max-w-4xl mx-auto">
        <div className="text-center mb-14">
          <h2 className="font-display text-3xl md:text-4xl font-bold mb-3">
            How <span className="gradient-text">Vinaval AI</span> Works
          </h2>
          <p className="text-slate-400">Simple. Focused. Powerful.</p>
        </div>

        <div className="space-y-4">
          {[
            { step: '01', title: 'Sign in with Google', desc: 'One-click authentication. Your data stays private.' },
            { step: '02', title: 'Select Your Exam', desc: 'Choose NEET or TNPSC. Your workspace adapts to your exam.' },
            { step: '03', title: 'Create a Learning Space', desc: 'Pick a subject (and optionally a topic) to focus your session.' },
            { step: '04', title: 'Learn, Practice & Analyze', desc: 'Use all 6 modules — grounded AI answers, practice tests, exam lab, and more.' },
          ].map((item, i) => (
            <div key={i} className="flex items-start gap-5 glass-card rounded-2xl p-5">
              <div className="w-12 h-12 rounded-xl bg-gradient-brand flex items-center justify-center flex-shrink-0 shadow-lg shadow-brand-500/30">
                <span className="font-display font-bold text-sm text-white">{item.step}</span>
              </div>
              <div>
                <div className="font-semibold text-white mb-1">{item.title}</div>
                <div className="text-slate-400 text-sm">{item.desc}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── Trust / Quality ─────────────────────── */}
      <section className="relative z-10 px-6 py-16 max-w-4xl mx-auto">
        <div className="glass-card rounded-3xl p-8 text-center">
          <Shield className="w-10 h-10 text-brand-400 mx-auto mb-4" />
          <h3 className="font-display text-xl font-bold mb-3">Built for Accuracy, Not Impressiveness</h3>
          <p className="text-slate-400 text-sm max-w-2xl mx-auto mb-6">
            Every AI answer is grounded in indexed Tamil Nadu State Board textbooks using Retrieval-Augmented Generation.
            If the answer isn't in the books, Vinaval AI will tell you — never hallucinate.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            {['State Board Textbooks', 'Metadata Filtering', 'Subject Isolation', 'Groq LLM', 'ChromaDB'].map((tag) => (
              <span key={tag} className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium bg-brand-500/10 text-brand-300 border border-brand-500/20">
                <CheckCircle2 className="w-3.5 h-3.5" />
                {tag}
              </span>
            ))}
          </div>
        </div>
      </section>

      {/* ── Final CTA ───────────────────────────── */}
      <section className="relative z-10 px-6 py-24 text-center max-w-3xl mx-auto">
        <h2 className="font-display text-4xl md:text-5xl font-extrabold mb-5">
          Ready to Study <span className="gradient-text">Smarter?</span>
        </h2>
        <p className="text-slate-400 text-lg mb-10">
          Join Tamil Nadu aspirants learning with AI that actually knows your syllabus.
        </p>
        <button
          id="footer-signin-btn"
          onClick={handleGoogleLogin}
          className="btn-primary text-lg px-10 py-4 rounded-2xl mx-auto"
        >
          Get Started — It's Free
          <ArrowRight className="w-5 h-5" />
        </button>
      </section>

      {/* ── Footer ──────────────────────────────── */}
      <footer className="relative z-10 border-t border-white/5 px-6 py-8">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-brand-400" />
            <span className="font-display font-bold text-white text-sm">Vinaval AI</span>
          </div>
          <p className="text-slate-600 text-xs">
            © 2026 Vinaval AI · AI Learning Arena for Tamil Nadu Aspirants
          </p>
        </div>
      </footer>
    </div>
  )
}
