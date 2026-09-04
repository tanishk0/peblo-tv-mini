import { createContext, useContext, useEffect, useState } from 'react'
import { api, authStore } from './api'
import type { User } from './types'

type Auth = { user: User | null; loading: boolean; login: (email: string, password: string) => Promise<void>; logout: () => void }
const AuthContext = createContext<Auth | null>(null)
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null); const [loading, setLoading] = useState(true)
  useEffect(() => {
    const unauthenticated = () => setUser(null)
    window.addEventListener('peblo:unauthorized', unauthenticated)
    if (!authStore.get()) setLoading(false)
    else api.me().then(setUser).catch(() => authStore.clear()).finally(() => setLoading(false))
    return () => window.removeEventListener('peblo:unauthorized', unauthenticated)
  }, [])
  const login = async (email: string, password: string) => { const result = await api.login(email, password); authStore.set(result.access_token); setUser(result.user) }
  const logout = () => { authStore.clear(); setUser(null) }
  return <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>
}
export const useAuth = () => { const value = useContext(AuthContext); if (!value) throw new Error('AuthProvider missing'); return value }
