import { useEffect, useReducer, useRef, useState, type ReactNode } from 'react'
import { AuthContext, sessionReducer } from '../auth'
import { ApiError, errorText, json, request } from '../api'
import type { User } from '../types'
import { queryClient } from '../query'
export default function AuthProvider({ children }: { children: ReactNode }) {
  const [session, dispatch] = useReducer(sessionReducer, { status: 'checking' })
  const [revision, setRevision] = useState(0)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const lock = useRef(false)
  useEffect(() => {
    const controller = new AbortController()
    let active = true
    request<User>('/auth/me', { signal: controller.signal })
      .then((user) => {
        if (active) dispatch({ type: 'user', user })
      })
      .catch((error) => {
        if (active)
          dispatch(
            error instanceof ApiError && error.status === 401
              ? { type: 'guest' }
              : { type: 'error', message: errorText(error) },
          )
      })
    const expired = () => {
      queryClient.clear()
      active = false
      controller.abort()
      dispatch({ type: 'guest' })
    }
    window.addEventListener('session-expired', expired)
    return () => {
      active = false
      controller.abort()
      window.removeEventListener('session-expired', expired)
    }
  }, [revision])
  async function logout() {
    if (lock.current) return
    lock.current = true
    setBusy(true)
    setMessage('')
    try {
      await request('/auth/logout', json('POST'))
      queryClient.clear()
      dispatch({ type: 'guest' })
    } catch (error) {
      setMessage(errorText(error))
    } finally {
      lock.current = false
      setBusy(false)
    }
  }
  return (
    <AuthContext.Provider
      value={{
        session,
        login: (user) => {
          queryClient.clear()
          setMessage('')
          dispatch({ type: 'user', user })
        },
        logout,
        retry: () => {
          dispatch({ type: 'check' })
          setRevision((v) => v + 1)
        },
        busy,
        message,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}