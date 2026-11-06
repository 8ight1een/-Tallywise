import { createContext, useContext } from 'react'
import type { User } from './types'
export type Session =
  | { status: 'checking' }
  | { status: 'guest' }
  | { status: 'error'; message: string }
  | { status: 'user'; user: User }
export type SessionAction =
  | { type: 'check' }
  | { type: 'guest' }
  | { type: 'user'; user: User }
  | { type: 'error'; message: string }
export function sessionReducer(_previous: Session, action: SessionAction): Session {
  switch (action.type) {
    case 'check':
      return { status: 'checking' }
    case 'guest':
      return { status: 'guest' }
    case 'user':
      return { status: 'user', user: action.user }
    case 'error':
      return { status: 'error', message: action.message }
  }
}
type AuthValue = {
  session: Session
  login: (user: User) => void
  logout: () => Promise<void>
  retry: () => void
  busy: boolean
  message: string
}
export const AuthContext = createContext<AuthValue | null>(null)
export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth必须位于AuthProvider内部')
  return value
}