import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import './web-electron-shim'
import App from './App'
import { ErrorBoundary } from './components/ErrorBoundary'
import { LangProvider } from './i18n'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <LangProvider>
      <HashRouter>
        <ErrorBoundary>
          <App />
        </ErrorBoundary>
      </HashRouter>
    </LangProvider>
  </StrictMode>
)
