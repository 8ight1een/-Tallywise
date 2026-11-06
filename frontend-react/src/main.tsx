import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './auth.css'
import './workspace.css'
import App from './App'
import ErrorBoundary from './components/ErrorBoundary'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from './query'
import AuthProvider from './components/AuthProvider'
import { BrowserRouter } from 'react-router'
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <AuthProvider>
            <App />
          </AuthProvider>
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  </StrictMode>,
)