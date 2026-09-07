import { useCallback, useEffect, useMemo, useState } from 'react'

import {
  api,
  clearStoredToken,
  getStoredToken,
  setUnauthorizedHandler,
  storeToken,
} from '../api/client'
import { AuthContext } from './context'

export function AuthProvider({ children }) {
  const [token, setToken] = useState(getStoredToken)
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)
  const logout = useCallback(() => {
    clearStoredToken()
    setToken(null)
    setUser(null)
  }, [])

  useEffect(() => {
    setUnauthorizedHandler(logout)
    return () => setUnauthorizedHandler(() => {})
  }, [logout])

  useEffect(() => {
    async function loadCurrentUser() {
      if (!getStoredToken()) {
        setLoading(false)
        return
      }
      try {
        setUser(await api.getCurrentUser())
      } catch {
        logout()
      } finally {
        setLoading(false)
      }
    }
    loadCurrentUser()
  }, [logout])

  const login = useCallback(async (email, password) => {
    const response = await api.login({ email, password })
    storeToken(response.access_token)
    setToken(response.access_token)
    const currentUser = await api.getCurrentUser()
    setUser(currentUser)
    return currentUser
  }, [])
  const register = useCallback(
    (email, password) => api.register({ email, password }),
    [],
  )
  const value = useMemo(
    () => ({ user, token, loading, login, logout, register }),
    [loading, login, logout, register, token, user],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
