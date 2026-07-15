import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react'
import { authService, User } from '../services/authService'

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  signInWithGoogle: () => Promise<void>
  logout: () => Promise<void>
  updateUser: (patch: Partial<User>) => void
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => authService.getCachedUser())

  const signInWithGoogle = useCallback(async () => {
    const tokenData = await authService.signInWithGoogle()
    authService.saveSession(tokenData)
    setUser(tokenData.user)
  }, [])

  const logout = useCallback(async () => {
    await authService.signOut()
    setUser(null)
  }, [])

  const updateUser = useCallback((patch: Partial<User>) => {
    setUser((prev) => {
      if (!prev) return prev
      const updated = { ...prev, ...patch }
      // Keep localStorage in sync
      localStorage.setItem('vinaval_user', JSON.stringify(updated))
      return updated
    })
  }, [])

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, signInWithGoogle, logout, updateUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within <AuthProvider>')
  return ctx
}
