import { Navigate, Route, Routes } from 'react-router'
import { useAuth } from './auth'
import AuthPage from './pages/AuthPage'
import LedgerPage from './pages/LedgerPage'
import Workspace from './components/Workspace'
import { labels, type Page } from './workspace'
export default function App() {
  const { session, login, logout, retry, busy, message } = useAuth()
  if (session.status === 'checking')
    return <p className="status">正在确认登录状态…</p>
  if (session.status === 'error')
    return (
      <div className="status" role="alert">
        {session.message}
        <button onClick={retry}>重试</button>
      </div>
    )
  if (session.status === 'guest')
    return (
      <Routes>
        <Route path="/login" element={<AuthPage onLogin={login} />} />
        <Route path="/register" element={<AuthPage onLogin={login} />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    )
  const user = session.user
  return (
    <>
      <p className="form-error" role="status">
        {message}
      </p>
      <Routes>
        <Route path="/" element={<Navigate to="/overview" replace />} />
        <Route path="/login" element={<Navigate to="/overview" replace />} />
        <Route path="/register" element={<Navigate to="/overview" replace />} />
        {(Object.keys(labels) as Page[]).map((page) => (
          <Route
            key={page}
            path={'/' + page}
            element={
              <Workspace
                page={page}
                name={user.nickname || user.email}
                onLogout={logout}
                logoutBusy={busy}
              >
                <LedgerPage page={page} />
              </Workspace>
            }
          />
        ))}
        <Route
          path="*"
          element={
            <div className="status">
              页面不存在。<a href="/">返回首页</a>
            </div>
          }
        />
      </Routes>
    </>
  )
}