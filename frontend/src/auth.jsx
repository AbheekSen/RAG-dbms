import { createContext, useContext, useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { api, getToken } from './api'

const AuthCtx = createContext(null)
export const useAuth = () => useContext(AuthCtx)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(!!getToken())

  useEffect(() => {
    if (!getToken()) return
    api('/auth/me').then(setUser).catch(() => localStorage.removeItem('token')).finally(() => setLoading(false))
  }, [])

  const authenticate = async (mode, payload) => {
    const data = await api(`/auth/${mode}`, { method: 'POST', body: payload })
    localStorage.setItem('token', data.token)
    setUser(data.user)
  }
  const logout = () => { localStorage.removeItem('token'); setUser(null) }

  return <AuthCtx.Provider value={{ user, loading, authenticate, logout }}>{children}</AuthCtx.Provider>
}

export function Protected({ children, admin }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="p-10 text-slate-500">Loading…</div>
  if (!user) return <Navigate to="/login" replace />
  if (admin && user.role !== 'admin') return <Navigate to="/" replace />
  return children
}
