import { Navigate, Route, Routes } from 'react-router'
import AuthPage from './pages/AuthPage'

export default function App() {
  return <Routes>
    <Route path="/login" element={<AuthPage />} />
    <Route path="*" element={<Navigate to="/login" replace />} />
  </Routes>
}
