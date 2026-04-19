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
  const [token, setTokenState] = useState<string | null>(null)
  const [user, setUser] = useState<AuthUser | null>(null)

  useEffect(() => {
    const stored = getToken()
    if (!stored) return
    setTokenState(stored)
    // Restore user state from stored token
    getMe()
      .then((u) => setUser(u))
      .catch(() => {
        // Token is invalid or expired — clear it
        clearToken()
        setTokenState(null)
      })
  }, [])

  async function login(email: string, password: string) {
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
