import { useEffect, useRef } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { authService } from '../services/authService'

/**
 * GoogleCallback — This page is loaded after Google redirects back.
 * URL: /auth/callback?code=...
 * It exchanges the code for a JWT, saves the session, and redirects to /select-exam.
 */
export default function GoogleCallback() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { login } = useAuth()
  const called = useRef(false) // prevent double-invocation in StrictMode

  useEffect(() => {
    if (called.current) return
    called.current = true

    const code = searchParams.get('code')
    if (!code) {
      navigate('/?error=no_code')
      return
    }

    authService
      .googleCallback(code)
      .then((data) => {
        login(data)
        navigate('/select-exam', { replace: true })
      })
      .catch(() => {
        navigate('/?error=auth_failed')
      })
  }, [])

  return (
    <div className="min-h-screen bg-surface-900 flex items-center justify-center">
      <div className="text-center space-y-4">
        <div className="w-16 h-16 mx-auto rounded-full border-4 border-brand-500/30 border-t-brand-500 animate-spin" />
        <p className="text-slate-400 text-sm">Signing you in…</p>
      </div>
    </div>
  )
}
