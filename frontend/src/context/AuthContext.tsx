// frontend/src/context/AuthContext.tsx
'use client'

import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from 'react'
import { loginUser, registerUser, getMe, AuthUser } from '@/lib/api'
import { getToken, setToken, clearToken } from '@/lib/auth'

type AuthState = {
  token: string | null
  user: AuthUser | null
  login: (email: string, password: string) => Promise<void>
  register: (
    email: string,
    password: string,
    displayName?: string
  ) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const isMock = process.env.NEXT_PUBLIC_MOCK_AUTH === 'true'
  const [token, setTokenState] = useState<string | null>(() => getToken())
  const [user, setUser] = useState<AuthUser | null>(() => {
    if (!isMock || !getToken()) return null
    return { id: 'mock-user', email: 'dev@mock.local', display_name: 'Dev User' }
  })

  useEffect(() => {
    if (!token || isMock) return
    let active = true
    // Restore user state from stored token
    getMe()
      .then((u) => {
        if (active) setUser(u)
      })
      .catch(() => {
        if (!active) return
        // Token is invalid or expired — clear it
        clearToken()
        setTokenState(null)
        setUser(null)
      })
    return () => {
      active = false
    }
  }, [isMock, token])

  async function login(email: string, password: string) {
    if (isMock) {
      const mockToken = 'mock-token'
      setToken(mockToken)
      setTokenState(mockToken)
      setUser({ id: `mock-${email}`, email, display_name: 'Dev User' })
      return
    }
    const data = await loginUser(email, password)
    setToken(data.access_token)
    setTokenState(data.access_token)
    setUser(data.user)
  }

  async function register(
    email: string,
    password: string,
    displayName?: string
  ) {
    if (isMock) {
      const mockToken = 'mock-token'
      setToken(mockToken)
      setTokenState(mockToken)
      setUser({ id: `mock-${email}`, email, display_name: displayName ?? 'Dev User' })
      return
    }
    const data = await registerUser(email, password, displayName)
    setToken(data.access_token)
    setTokenState(data.access_token)
    setUser(data.user)
  }

  function logout() {
    clearToken()
    setTokenState(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ token, user, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
