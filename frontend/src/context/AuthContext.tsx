import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { getMe, type UserMe } from '../api/auth'

interface AuthContextType {
  user: UserMe | null
  token: string | null
  loading: boolean
  login: (token: string) => void
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserMe | null>(null)
  const [token, setTokenState] = useState<string | null>(() => localStorage.getItem('token'))
  const [loading, setLoading] = useState(true)

  const refreshUser = useCallback(async () => {
    const t = localStorage.getItem('token')
    if (!t) {
      setUser(null)
      return
    }
    try {
      const { data } = await getMe()
      setUser(data)
    } catch {
      localStorage.removeItem('token')
      setTokenState(null)
      setUser(null)
    }
  }, [])

  useEffect(() => {
    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }
    refreshUser().finally(() => setLoading(false))
  }, [token, refreshUser])

  const login = useCallback((newToken: string) => {
    localStorage.setItem('token', newToken)
    setTokenState(newToken)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    setTokenState(null)
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
