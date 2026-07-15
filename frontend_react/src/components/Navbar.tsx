import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Brain, ChevronDown, LogOut, LayoutDashboard, BookOpen } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

interface NavbarProps {
  examName?: string
}

export default function Navbar({ examName }: NavbarProps) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

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
    <nav style={{ borderBottom: '1px solid var(--border)', backgroundColor: 'var(--bg)' }}
         className="sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-13 flex items-center justify-between gap-4"
           style={{ height: '52px' }}>

        {/* Logo */}
        <button
          onClick={() => navigate('/dashboard')}
          className="flex items-center gap-2 group"
        >
          <Brain className="w-5 h-5 transition-opacity group-hover:opacity-80"
                 style={{ color: 'var(--accent)' }} />
          <span className="font-semibold text-white text-sm">Vinaval AI</span>
        </button>

        {/* Nav links */}
        <div className="hidden sm:flex items-center gap-1">
          {examName && (
            <span className="text-xs px-2.5 py-1 rounded-md font-medium mr-2"
                  style={{ backgroundColor: 'var(--accent-soft)', color: 'var(--accent)', border: '1px solid rgba(90,127,245,0.2)' }}>
              {examName}
            </span>
          )}
          <button
            onClick={() => navigate('/select-exam')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs transition-colors"
            style={{ color: 'var(--text-muted)' }}
            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text)')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
          >
            <BookOpen className="w-3.5 h-3.5" />
            Switch Exam
          </button>
          <button
            onClick={() => navigate('/dashboard')}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs transition-colors"
            style={{ color: 'var(--text-muted)' }}
            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--text)')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
          >
            <LayoutDashboard className="w-3.5 h-3.5" />
            Dashboard
          </button>
        </div>

        {/* User dropdown */}
        <div className="relative" ref={dropdownRef}>
          <button
            id="user-avatar-btn"
            onClick={() => setDropdownOpen((prev) => !prev)}
            className="flex items-center gap-2 px-2 py-1.5 rounded-lg transition-colors"
            style={{ backgroundColor: dropdownOpen ? 'var(--bg-elevated)' : undefined }}
            onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
            onMouseLeave={(e) => { if (!dropdownOpen) e.currentTarget.style.backgroundColor = '' }}
          >
            {user?.avatar_url ? (
              <img src={user.avatar_url} alt={user.name}
                   className="w-7 h-7 rounded-full"
                   style={{ border: '1px solid var(--border)' }} />
            ) : (
              <div className="w-7 h-7 rounded-full flex items-center justify-center text-white text-xs font-semibold"
                   style={{ backgroundColor: 'var(--accent)' }}>
                {user?.name?.[0]?.toUpperCase() ?? 'U'}
              </div>
            )}
            <span className="hidden sm:block text-xs font-medium text-white max-w-[100px] truncate">
              {user?.name?.split(' ')[0]}
            </span>
            <ChevronDown className={`w-3.5 h-3.5 transition-transform ${dropdownOpen ? 'rotate-180' : ''}`}
                         style={{ color: 'var(--text-dim)' }} />
          </button>

          {dropdownOpen && (
            <div className="absolute right-0 mt-1.5 w-48 rounded-xl border shadow-lg overflow-hidden animate-fade-in"
                 style={{ backgroundColor: 'var(--bg-elevated)', borderColor: 'var(--border)', boxShadow: '0 8px 24px rgba(0,0,0,0.3)' }}>
              <div className="px-4 py-3" style={{ borderBottom: '1px solid var(--border-soft)' }}>
                <p className="text-xs font-semibold text-white truncate">{user?.name}</p>
                <p className="text-xs truncate mt-0.5" style={{ color: 'var(--text-dim)' }}>{user?.email}</p>
              </div>
              <button
                id="logout-btn"
                onClick={handleLogout}
                className="w-full flex items-center gap-2.5 px-4 py-2.5 text-xs transition-colors"
                style={{ color: 'var(--text-muted)' }}
                onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = 'rgba(248,113,113,0.08)'; e.currentTarget.style.color = 'var(--red)' }}
                onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = ''; e.currentTarget.style.color = 'var(--text-muted)' }}
              >
                <LogOut className="w-3.5 h-3.5" />
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </nav>
  )
}
