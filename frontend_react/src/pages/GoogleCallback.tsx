import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

/**
 * GoogleCallback — Legacy redirect handler (not currently used).
 * The app now uses Firebase popup sign-in via AuthContext.
 * This page just redirects to home if someone lands on it.
 */
export default function GoogleCallback() {
  const navigate = useNavigate()

  useEffect(() => {
    navigate('/', { replace: true })
  }, [navigate])

  return (
    <div className="min-h-screen bg-surface-900 flex items-center justify-center">
      <div className="text-center space-y-4">
        <div className="w-16 h-16 mx-auto rounded-full border-4 border-brand-500/30 border-t-brand-500 animate-spin" />
        <p className="text-slate-400 text-sm">Redirecting…</p>
      </div>
    </div>
  )
}
