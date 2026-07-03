import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Brain, ChevronDown, LogOut, LayoutDashboard, BookOpen } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

interface NavbarProps {
  examName?: string   // e.g. "NEET" or "TNPSC" — shown as a badge when inside the app
}

export default function Navbar({ examName }: NavbarProps) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleLogout = async () => {
    await logout()
    navigate('/')
  }

  return (
    <nav className="sticky top-0 z-50 border-b border-white/5 bg-surface-900/80 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">

        {/* ── Logo ───────────────────────────────── */}
        <button
          onClick={() => navigate('/dashboard')}
          className="flex items-center gap-2.5 group"
        >
          <div className="w-8 h-8 rounded-lg bg-gradient-brand flex items-center justify-center shadow-lg shadow-brand-500/30 group-hover:scale-105 transition-transform">
            <Brain className="w-4 h-4 text-white" />
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="font-display font-bold text-base text-white">Vinaval</span>
            <span className="font-display font-bold text-base gradient-text">AI</span>
          </div>
        </button>

        {/* ── Nav Links ──────────────────────────── */}
        <div className="hidden sm:flex items-center gap-1">
          <button
            onClick={() => navigate('/select-exam')}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 text-sm transition-all"
          >
            <BookOpen className="w-4 h-4" />
            Switch Exam
          </button>
          <button
            onClick={() => navigate('/dashboard')}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-slate-400 hover:text-white hover:bg-white/5 text-sm transition-all"
          >
            <LayoutDashboard className="w-4 h-4" />
            Dashboard
          </button>
        </div>

        {/* ── Right Side ─────────────────────────── */}
        <div className="flex items-center gap-3">
          {/* Exam badge */}
          {examName && (
            <span className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold bg-brand-500/15 text-brand-300 border border-brand-500/25">
              <span className="w-1.5 h-1.5 rounded-full bg-brand-400 animate-pulse" />
              {examName}
            </span>
          )}

          {/* User avatar dropdown */}
          <div className="relative" ref={dropdownRef}>
            <button
              id="user-avatar-btn"
              onClick={() => setDropdownOpen(prev => !prev)}
              className="flex items-center gap-2 px-2 py-1.5 rounded-xl hover:bg-white/5 transition-all group"
            >
              {user?.avatar_url ? (
                <img
                  src={user.avatar_url}
                  alt={user.name}
                  className="w-8 h-8 rounded-full ring-2 ring-brand-500/30"
                />
              ) : (
                <div className="w-8 h-8 rounded-full bg-gradient-brand flex items-center justify-center text-white text-sm font-bold">
                  {user?.name?.[0]?.toUpperCase() ?? 'U'}
                </div>
              )}
              <div className="hidden sm:block text-left">
                <div className="text-xs font-semibold text-white leading-none">{user?.name}</div>
                <div className="text-xs text-slate-500 mt-0.5 leading-none">{user?.email}</div>
              </div>
              <ChevronDown className={`w-3.5 h-3.5 text-slate-500 transition-transform ${dropdownOpen ? 'rotate-180' : ''}`} />
            </button>

            {/* Dropdown menu */}
            {dropdownOpen && (
              <div className="absolute right-0 mt-2 w-48 glass-card rounded-xl border border-white/10 shadow-xl shadow-black/40 overflow-hidden animate-fade-in">
                <div className="px-4 py-3 border-b border-white/5">
                  <p className="text-xs font-semibold text-white truncate">{user?.name}</p>
                  <p className="text-xs text-slate-500 truncate">{user?.email}</p>
                </div>
                <button
                  id="logout-btn"
                  onClick={handleLogout}
                  className="w-full flex items-center gap-2.5 px-4 py-3 text-sm text-slate-300 hover:text-white hover:bg-white/5 transition-colors"
                >
                  <LogOut className="w-4 h-4 text-rose-400" />
                  Sign out
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}
