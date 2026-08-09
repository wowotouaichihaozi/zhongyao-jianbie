import { useEffect, useState } from 'react'
import { Routes, Route, Navigate, useLocation, matchPath } from 'react-router-dom'
import { Sidebar } from './components/layout/Sidebar'
import { HomePage } from './pages/home'
import { SessionCreatePage } from './pages/session-create'
import { ThinkingDetailPage } from './pages/thinking-detail'
import { SessionsPage } from './pages/sessions'
import { SessionDetailPage } from './pages/session-detail'
import { SessionGeneratingPage } from './pages/session-generating'
import { TemplateSessionsGeneratingPage } from './pages/template-sessions-generating'
import { StylesPage } from './pages/styles'
import { FontsPage } from './pages/fonts'
import { StyleEditorPage } from './pages/style-editor'
import { TemplatesPage } from './pages/templates'
import { AppToaster } from './components/AppToaster'
import { UpdateAvailableDialog } from './components/UpdateAvailableDialog'
import { ScrollArea } from './components/ui/ScrollArea'
import { ipc } from './lib/ipc'
import type { UpdateAvailablePayload } from '@shared/app-update.js'
import { useGenerationNotifications } from './hooks/useGenerationNotifications'
import { LogOut } from 'lucide-react'

function ExitToResourcesLink(): React.JSX.Element {
  return (
    <a
      href="/personalized-resources"
      target="_top"
      className="fixed left-4 top-4 z-[200] inline-flex h-10 items-center gap-2 rounded-lg border border-[#cfe5da] bg-white/95 px-3.5 text-[12px] font-semibold text-[#36584a] shadow-[0_10px_28px_rgba(36,76,59,0.14)] backdrop-blur transition-colors hover:border-[#8fd5b4] hover:bg-[#eefaf4] hover:text-[#117a51]"
      aria-label="返回个性化资源"
      title="返回个性化资源"
    >
      <LogOut className="h-4 w-4" aria-hidden="true" />
      <span>返回个性化资源</span>
    </a>
  )
}

function App(): React.JSX.Element {
  const location = useLocation()
  useGenerationNotifications()
  const isSessionDetailRoute = Boolean(matchPath('/sessions/:id/*', location.pathname))
  const isThinkingRoute = Boolean(matchPath('/thinking', location.pathname))
  const [availableUpdate, setAvailableUpdate] = useState<UpdateAvailablePayload | null>(null)

  useEffect(() => {
    const unsubscribe = ipc.onUpdateAvailable((update) => {
      setAvailableUpdate(update)
    })
    return () => {
      unsubscribe?.()
    }
  }, [])

  if (isSessionDetailRoute) {
    return (
      <>
        <div className="flex h-full min-h-0 flex-col overflow-hidden bg-background text-foreground">
          <Routes>
            <Route path="/sessions/:id/template-generating" element={<TemplateSessionsGeneratingPage />} />
            <Route path="/sessions/:id/generating" element={<SessionGeneratingPage />} />
            <Route path="/sessions/:id" element={<SessionDetailPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
        <ExitToResourcesLink />
        <UpdateAvailableDialog update={availableUpdate} onClose={() => setAvailableUpdate(null)} />
        <AppToaster />
      </>
    )
  }

  return (
    <>
      <div className="h-full min-h-0 overflow-hidden bg-background text-foreground">
        <div className="flex h-full min-h-0 flex-col">
          <div className="app-drag-region app-titlebar bg-background/88 backdrop-blur-xl" />

          <div className="flex min-h-0 flex-1">
            <aside className="hidden min-h-0 w-[240px] shrink-0 flex-col border-r border-border/70 bg-white/58 md:flex">
              <Sidebar />
            </aside>
            {isThinkingRoute ? (
              <div className="min-h-0 flex-1 overflow-hidden">
                <Routes>
                  <Route path="/thinking" element={<ThinkingDetailPage />} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </div>
            ) : (
              <ScrollArea className="min-h-0 flex-1">
                <Routes>
                  <Route path="/" element={<HomePage />} />
                  <Route path="/create/session" element={<SessionCreatePage />} />
                  <Route path="/sessions" element={<SessionsPage />} />
                  <Route path="/templates" element={<TemplatesPage />} />
                  <Route path="/styles" element={<StylesPage />} />
                  <Route path="/fonts" element={<FontsPage />} />
                  <Route path="/styles/new" element={<StyleEditorPage />} />
                  <Route path="/styles/:styleId" element={<StyleEditorPage />} />
                  <Route path="/settings" element={<Navigate to="/" replace />} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </ScrollArea>
            )}
          </div>
        </div>
      </div>
      <ExitToResourcesLink />
      <UpdateAvailableDialog update={availableUpdate} onClose={() => setAvailableUpdate(null)} />
      <AppToaster />
    </>
  )
}

export default App
