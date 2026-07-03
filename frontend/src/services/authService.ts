import { signInWithPopup, signOut as firebaseSignOut } from 'firebase/auth'
import { auth, googleProvider } from '../lib/firebase'
import api from './api'

export interface User {
  id: number
  email: string
  name: string
  avatar_url: string | null
  created_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

export const authService = {
  /**
   * Open Google sign-in popup via Firebase.
   * On success, gets the Firebase ID token, sends it to our backend,
   * and receives a JWT for all subsequent API calls.
   */
  async signInWithGoogle(): Promise<TokenResponse> {
    // Step 1: Firebase popup sign-in
    const result = await signInWithPopup(auth, googleProvider)

    // Step 2: Get the Firebase ID token
    const idToken = await result.user.getIdToken()

    // Step 3: Exchange Firebase ID token for our app's JWT
    const { data } = await api.post<TokenResponse>('/auth/firebase', { id_token: idToken })
    return data
  },

  /**
   * Sign out from Firebase and clear local session.
   */
  async signOut(): Promise<void> {
    await firebaseSignOut(auth)
    authService.clearSession()
  },

  /**
   * Fetch the currently authenticated user from backend.
   */
  async getMe(): Promise<User> {
    const { data } = await api.get<User>('/auth/me')
    return data
  },

  saveSession(tokenData: TokenResponse): void {
    localStorage.setItem('vinaval_token', tokenData.access_token)
    localStorage.setItem('vinaval_user', JSON.stringify(tokenData.user))
  },

  clearSession(): void {
    localStorage.removeItem('vinaval_token')
    localStorage.removeItem('vinaval_user')
  },

  getCachedUser(): User | null {
    const raw = localStorage.getItem('vinaval_user')
    if (!raw) return null
    try {
      return JSON.parse(raw) as User
    } catch {
      return null
    }
  },

  isAuthenticated(): boolean {
    return !!localStorage.getItem('vinaval_token')
  },
}
