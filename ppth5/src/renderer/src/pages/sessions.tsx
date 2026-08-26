import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '../components/ui/Button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card'
import { Input } from '../components/ui/Input'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '../components/ui/Dialog'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../components/ui/Tooltip'
import { Cloud, FileArchive, FileText, FileUp, FolderOpen, LayoutTemplate, LoaderCircle, MessageSquare, MessagesSquare, Pencil, RefreshCw, Sparkles, Trash2, X, type LucideIcon } from 'lucide-react'
import { type Session, useSessionStore, useTemplateStore } from '../store'
import { useToastStore } from '../store'
import { ipc, type GenerateRunStateSnapshot } from '../lib/ipc'
import { getEditorGate, parseSessionMetadata } from '../lib/sessionMetadata'
import { useT } from '../i18n'
import { SaveTemplateDialog } from '../components/templates/SaveTemplateDialog'
import dayjs from 'dayjs'
import duration from 'dayjs/plugin/duration'

dayjs.extend(duration)

type ActiveGenerateRun = GenerateRunStateSnapshot & {
  status: 'queued' | 'running'
}

type PlatformPptTask = {
  taskId: string
  title?: string
  prompt?: string
  status: 'queued' | 'running' | 'complete' | 'failed' | string
  route?: string
  result?: Record<string, unknown>
  error?: string
  createdAt?: string
  updatedAt?: string
}

type PlatformPptTaskView = {
  taskId: string
  title: string
  status: string
  statusText: string
  statusClassName: string
  progress: number
  pageCount: number
  generatedCount: number
  route: string
  error: string
  updatedAt: string
}

const asRecord = (value: unknown): Record<string, unknown> =>
  value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}

const clampTaskProgress = (value: unknown): number => {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? Math.max(0, Math.min(100, Math.round(parsed))) : 0
}

const platformTaskView = (task: PlatformPptTask): PlatformPptTaskView => {
  const result = asRecord(task.result)
  const ppt = asRecord(result.ppt)
  const pages = Array.isArray(ppt.pages) ? ppt.pages : []
  const status = String(task.status || 'queued').toLowerCase()
  const progress = status === 'complete' ? 100 : clampTaskProgress(ppt.progress ?? result.progress)
  const pageCount = Math.max(1, Number(ppt.pageCount || result.pageCount || pages.length || 6))
  const statusMeta = status === 'complete'
    ? { text: '已完成', className: 'border-[#bad8b7] bg-[#eef9ec] text-[#4a7a46]' }
    : status === 'failed'
      ? { text: '生成失败', className: 'border-[#d7b5ae] bg-[#f3e8e6] text-[#93564f]' }
      : status === 'running'
        ? { text: `生成中 ${progress}%`, className: 'border-[#b7e6d0] bg-[#eefbf4] text-[#117a51]' }
        : { text: '排队中', className: 'border-[#d9c88c] bg-[#fff8df] text-[#886c16]' }
  const route = String(task.route || result.route || ppt.route || '')
  return {
    taskId: task.taskId,
    title: String(task.title || ppt.title || result.topic || task.prompt || '中医学习课件'),
    status,
    statusText: statusMeta.text,
    statusClassName: statusMeta.className,
    progress,
    pageCount,
    generatedCount: pages.length,
    route,
    error: String(task.error || ppt.error || result.qualityError || ''),
    updatedAt: String(task.updatedAt || task.createdAt || '')
  }
}

const getSourceTag = (
  session: Session,
  labels: { pptx: string; sessionFile: string; saveAsNew: string; document: string; ai: string; thinking: string; template: string }
): { label: string; Icon: LucideIcon; className: string; iconClassName: string } => {
  const metadata = parseSessionMetadata(session.metadata)
  const source = typeof metadata.source === 'string' ? metadata.source : ''
  if (source === 'session-save-as-new') {
    return {
      label: labels.saveAsNew,
      Icon: FileArchive,
      className:
        'border-[#6fc2aa]/50 bg-[#e8f8f3] text-[#1f6f5f] shadow-[inset_0_1px_0_rgba(255,255,255,0.75)]',
      iconClassName: 'text-[#189072]'
    }
  }
  if (source === 'template' || source === 'template-direct-edit' || session.model === 'template-direct-edit') {
    return {
      label: labels.template,
      Icon: LayoutTemplate,
      className:
        'border-[#e48aa5]/50 bg-[#fff0f5] text-[#8b3352] shadow-[inset_0_1px_0_rgba(255,255,255,0.75)]',
      iconClassName: 'text-[#c94672]'
    }
  }
  if (source === 'session-file-import' || session.model === 'session-file-import') {
    return {
      label: labels.sessionFile,
      Icon: FileArchive,
      className:
        'border-[#b7e6d0]/55 bg-[#eefbf4] text-[#117a51] shadow-[inset_0_1px_0_rgba(255,255,255,0.75)]',
      iconClassName: 'text-[#21b978]'
    }
  }
  if (source === 'pptx-import' || session.provider === 'import' || session.model === 'pptx-import') {
    return {
      label: labels.pptx,
      Icon: FileUp,
      className:
        'border-[#58d89c]/55 bg-[#eefbf4] text-[#117a51] shadow-[inset_0_1px_0_rgba(255,255,255,0.75)]',
      iconClassName: 'text-[#21b978]'
    }
  }
  if (source === 'thinking') {
    return {
      label: labels.thinking,
      Icon: MessagesSquare,
      className:
        'border-[#82c86a]/55 bg-[#effbe9] text-[#38702c] shadow-[inset_0_1px_0_rgba(255,255,255,0.75)]',
      iconClassName: 'text-[#4a9e39]'
    }
  }
  if (session.referenceDocumentPath || session.reference_document_path) {
    return {
      label: labels.document,
      Icon: FileText,
      className:
        'border-[#82c86a]/55 bg-[#effbe9] text-[#38702c] shadow-[inset_0_1px_0_rgba(255,255,255,0.75)]',
      iconClassName: 'text-[#ad7d10]'
    }
  }
  return {
    label: labels.ai,
    Icon: Sparkles,
    className:
      'border-[#82c86a]/55 bg-[#effbe9] text-[#38702c] shadow-[inset_0_1px_0_rgba(255,255,255,0.75)]',
    iconClassName: 'text-[#d87721]'
  }
}

export function SessionsPage(): React.JSX.Element {
  const navigate = useNavigate()
  const { sessions, fetchSessions, deleteSession, updateSessionTitle, importSessionFile } = useSessionStore()
  const { createTemplateFromSession } = useTemplateStore()
  const { success, error } = useToastStore()
  const t = useT()
  const [renameSession, setRenameSession] = useState<Session | null>(null)
  const [renameTitle, setRenameTitle] = useState('')
  const [renaming, setRenaming] = useState(false)
  const [deleteSessionTarget, setDeleteSessionTarget] = useState<Session | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [importingSession, setImportingSession] = useState(false)
  const [saveTemplateTarget, setSaveTemplateTarget] = useState<Session | null>(null)
  const [savingTemplate, setSavingTemplate] = useState(false)
  const [activeRuns, setActiveRuns] = useState<Record<string, ActiveGenerateRun>>({})
  const [platformTasks, setPlatformTasks] = useState<PlatformPptTask[]>([])
  const [platformLoading, setPlatformLoading] = useState(true)
  const [platformError, setPlatformError] = useState('')
  const [platformRefreshToken, setPlatformRefreshToken] = useState(0)

  useEffect(() => {
    void fetchSessions()
  }, [fetchSessions])

  useEffect(() => {
    let mounted = true
    let timer: ReturnType<typeof setTimeout> | undefined

    const loadPlatformTasks = async (): Promise<void> => {
      setPlatformLoading(true)
      try {
        const response = await fetch('/api/personalized-resources/ppt/tasks?limit=60', {
          credentials: 'include',
          headers: { Accept: 'application/json' }
        })
        const payload = (await response.json().catch(() => ({}))) as {
          code?: number
          msg?: string
          data?: { tasks?: PlatformPptTask[] }
        }
        if (!response.ok || payload.code !== 0) {
          throw new Error(payload.msg || `HTTP ${response.status}`)
        }
        if (!mounted) return
        const tasks = Array.isArray(payload.data?.tasks) ? payload.data.tasks : []
        setPlatformTasks(tasks)
        setPlatformError('')
        const hasActiveTask = tasks.some((task) => task.status === 'queued' || task.status === 'running')
        timer = setTimeout(() => void loadPlatformTasks(), hasActiveTask ? 2500 : 12000)
      } catch (err) {
        if (!mounted) return
        setPlatformError(err instanceof Error ? err.message : '历史记录加载失败')
        timer = setTimeout(() => void loadPlatformTasks(), 12000)
      } finally {
        if (mounted) setPlatformLoading(false)
      }
    }

    void loadPlatformTasks()
    return () => {
      mounted = false
      if (timer) clearTimeout(timer)
    }
  }, [platformRefreshToken])

  useEffect(() => {
    let mounted = true
    void ipc
      .listActiveGenerateRuns()
      .then((runs) => {
        if (!mounted) return
        setActiveRuns(
          Object.fromEntries(
            runs
              .filter((run): run is ActiveGenerateRun => run.status === 'queued' || run.status === 'running')
              .map((run) => [run.sessionId, run])
          )
        )
      })
      .catch(() => {})

    const unsubscribe = ipc.onGenerateChunk((chunk) => {
      const sessionId = chunk.payload.sessionId
      if (!sessionId) return
      if (chunk.type === 'run_completed' || chunk.type === 'run_error') {
        void fetchSessions()
      }
      setActiveRuns((prev) => {
        if (chunk.type === 'run_completed' || chunk.type === 'run_error') {
          const previous = prev[sessionId]
          if (!previous || previous.runId !== chunk.payload.runId) return prev
          const next = { ...prev }
          delete next[sessionId]
          return next
        }
        const previous = prev[sessionId]
        if (previous?.runId && previous.runId !== chunk.payload.runId) return prev
        const stage = 'stage' in chunk.payload ? chunk.payload.stage : ''
        const completedPageCount =
          'completedPageCount' in chunk.payload &&
          typeof chunk.payload.completedPageCount === 'number'
            ? chunk.payload.completedPageCount
            : previous?.completedPageCount || 0
        const failedPageCount =
          'failedPageCount' in chunk.payload && typeof chunk.payload.failedPageCount === 'number'
            ? chunk.payload.failedPageCount
            : previous?.failedPageCount || 0
        return {
          ...prev,
          [sessionId]: {
            sessionId,
            runId: chunk.payload.runId,
            status: stage === 'queued' ? 'queued' : 'running',
            hasActiveRun: true,
            progress:
              'progress' in chunk.payload && typeof chunk.payload.progress === 'number'
                ? Math.max(0, Math.min(90, Math.floor(chunk.payload.progress)))
                : previous?.progress || 0,
            totalPages:
              'totalPages' in chunk.payload && typeof chunk.payload.totalPages === 'number'
                ? Math.max(1, Math.floor(chunk.payload.totalPages))
                : previous?.totalPages || 1,
            events: previous?.events || [],
            error: null,
            startedAt: previous?.startedAt || Date.now(),
            updatedAt: Date.now(),
            kind: previous?.kind,
            completedPageCount,
            failedPageCount
          }
        }
      })
    })

    return () => {
      mounted = false
      unsubscribe?.()
    }
  }, [fetchSessions])

  const sortedSessions = sessions
  const platformTaskViews = platformTasks.map(platformTaskView)

  const openPlatformTask = (task: PlatformPptTaskView): void => {
    if (!task.route.startsWith('/')) return
    const url = new URL(task.route, window.location.origin)
    if (!url.searchParams.has('xzTask')) url.searchParams.set('xzTask', task.taskId)
    window.location.assign(`${url.pathname}${url.search}${url.hash}`)
  }
  const canEnterEditor = (session: {
    id: string
    status: string
    metadata: string | null
    page_count: number | null
  }): boolean => getEditorGate(session, 0.68).canEdit

  const getSessionRoute = (session: { id: string; status: string; metadata: string | null; page_count: number | null }): string => {
    const activeRun = activeRuns[session.id]
    const metadata = parseSessionMetadata(session.metadata)
    if (activeRun) {
      return activeRun.kind === 'template' || metadata.source === 'template'
        ? `/sessions/${session.id}/template-generating`
        : `/sessions/${session.id}/generating`
    }
    if (canEnterEditor(session)) return `/sessions/${session.id}`
    return metadata.source === 'template'
      ? `/sessions/${session.id}/template-generating`
      : `/sessions/${session.id}/generating`
  }

  const openRenameDialog = (session: Session): void => {
    setRenameSession(session)
    setRenameTitle(session.title)
  }

  const closeRenameDialog = (): void => {
    if (renaming) return
    setRenameSession(null)
    setRenameTitle('')
  }

  const handleRenameSubmit = async (): Promise<void> => {
    if (!renameSession) return
    const title = renameTitle.trim()
    if (!title) {
      error(t('sessions.titleEmpty'))
      return
    }
    if (title.length > 120) {
      error(t('sessions.titleTooLong'), { description: t('sessions.titleTooLongDescription') })
      return
    }
    setRenaming(true)
    try {
      await updateSessionTitle({ sessionId: renameSession.id, title })
      success(t('sessions.titleUpdated'))
      setRenameSession(null)
      setRenameTitle('')
    } catch (err) {
      error(t('sessions.renameFailed'), {
        description: err instanceof Error ? err.message : t('common.retryLater')
      })
    } finally {
      setRenaming(false)
    }
  }

  const closeDeleteDialog = (): void => {
    if (deleting) return
    setDeleteSessionTarget(null)
  }

  const handleDeleteSession = async (): Promise<void> => {
    if (!deleteSessionTarget) return
    setDeleting(true)
    try {
      await deleteSession(deleteSessionTarget.id)
      success(t('sessions.deleted'))
      setDeleteSessionTarget(null)
    } catch (err) {
      error(t('sessions.deleteFailed'), {
        description: err instanceof Error ? err.message : t('common.retryLater')
      })
    } finally {
      setDeleting(false)
    }
  }

  const handleImportSessionFile = async (): Promise<void> => {
    setImportingSession(true)
    try {
      const result = await importSessionFile()
      if (result.cancelled) return
      success(t('sessions.importDone'), {
        description: t('sessions.importedDescription', {
          title: result.title || t('sessions.importedFallbackTitle'),
          pageCount: result.pageCount || 0
        })
      })
    } catch (err) {
      error(t('sessions.importFailed'), {
        description: err instanceof Error ? err.message : t('common.retryLater')
      })
    } finally {
      setImportingSession(false)
    }
  }

  const handleSaveTemplate = async (payload: {
    name: string
    description: string
    tags: string[]
  }): Promise<void> => {
    if (!saveTemplateTarget || savingTemplate) return
    setSavingTemplate(true)
    try {
      await createTemplateFromSession({
        sessionId: saveTemplateTarget.id,
        ...payload
      })
      success(t('sessionDetail.templateSaved'), {
        action: {
          label: t('sessionDetail.viewTemplates'),
          onClick: () => navigate('/templates')
        }
      })
      setSaveTemplateTarget(null)
    } catch (err) {
      error(t('sessionDetail.templateSaveFailed'), {
        description: err instanceof Error ? err.message : t('common.retryLater')
      })
    } finally {
      setSavingTemplate(false)
    }
  }

  return (
    <div className="mx-auto w-full max-w-6xl p-6">
      <div className="mb-6">
        <p className="text-xs uppercase tracking-[0.22em] text-muted-foreground">{t('sessions.eyebrow')}</p>
        <div className="mt-2 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <h1 className="organic-serif text-[32px] font-semibold leading-none text-[#3e4a32]">{t('sessions.title')}</h1>
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-2 sm:justify-end">
            <TooltipProvider delayDuration={180}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button size="sm" variant="outline" className="min-w-[132px]" onClick={() => void handleImportSessionFile()} disabled={importingSession}>
                    <FileArchive className="mr-2 h-4 w-4" />
                    {importingSession ? t('sessions.importing') : t('sessions.importSessionFile')}
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="bottom" align="end" className="whitespace-pre-line">
                  {t('sessions.importSessionFileTooltip')}
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
            <Button size="sm" className="min-w-[112px]" onClick={() => navigate('/')}>
              <FolderOpen className="mr-2 h-4 w-4" />
              {t('sessions.newSession')}
            </Button>
          </div>
        </div>
      </div>

      <section className="mb-6" aria-labelledby="platform-ppt-history-title">
        <div className="mb-3 flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2">
            <Cloud className="h-5 w-5 shrink-0 text-[#189072]" />
            <h2 id="platform-ppt-history-title" className="truncate text-base font-semibold text-[#3e4a32]">
              学习路径与岐小智课件
            </h2>
            <span className="rounded-md bg-[#e8f8f3] px-2 py-0.5 text-xs font-semibold text-[#1f6f5f]">
              {platformTaskViews.length}
            </span>
          </div>
          <Button
            variant="outline"
            size="sm"
            title="刷新后台课件"
            aria-label="刷新后台课件"
            disabled={platformLoading}
            onClick={() => setPlatformRefreshToken((value) => value + 1)}
          >
            <RefreshCw className={`h-4 w-4 ${platformLoading ? 'animate-spin' : ''}`} />
          </Button>
        </div>

        {platformLoading && platformTaskViews.length === 0 ? (
          <div className="flex min-h-28 items-center justify-center rounded-lg border border-[#dce8e2] bg-white/75 text-sm text-muted-foreground">
            <LoaderCircle className="mr-2 h-5 w-5 animate-spin" />
            正在同步后台课件
          </div>
        ) : platformError && platformTaskViews.length === 0 ? (
          <div className="rounded-lg border border-[#e1c2bc] bg-[#fff5f3] px-4 py-5 text-sm text-[#93564f]">
            后台课件暂时无法加载：{platformError}
          </div>
        ) : platformTaskViews.length === 0 ? (
          <div className="rounded-lg border border-dashed border-[#cbd8d2] bg-white/60 px-4 py-8 text-center text-sm text-muted-foreground">
            暂无后台课件
          </div>
        ) : (
          <div className="grid gap-3">
            {platformTaskViews.map((task) => (
              <Card
                key={task.taskId}
                className={`transition-shadow ${task.route.startsWith('/') ? 'cursor-pointer hover:shadow-[0_12px_26px_rgba(45,86,72,0.12)]' : ''}`}
                onClick={() => openPlatformTask(task)}
              >
                <CardContent className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center">
                  <span className="grid h-10 w-10 shrink-0 place-items-center rounded-md bg-[#e8f8f3] text-[#189072]">
                    <FileText className="h-5 w-5" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <strong className="block truncate text-sm font-semibold text-[#34423a]">{task.title}</strong>
                    <small className="mt-1 block text-xs text-muted-foreground">
                      {task.updatedAt ? dayjs(task.updatedAt).format('YYYY/MM/DD HH:mm') : '时间待同步'}
                      {task.error ? ` · ${task.error}` : ''}
                    </small>
                  </span>
                  <span className="flex shrink-0 flex-wrap items-center gap-2 text-xs">
                    <span className={`rounded-md border px-2 py-1 font-semibold ${task.statusClassName}`}>
                      {task.statusText}
                    </span>
                    <span className="rounded-md border border-[#c8d6ba] bg-[#f0faf5] px-2 py-1 text-[#5d6b4d]">
                      {task.generatedCount}/{task.pageCount} 页
                    </span>
                  </span>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>

      <div className="mb-3 flex items-center gap-2">
        <h2 className="text-base font-semibold text-[#3e4a32]">工作台本地会话</h2>
        <span className="rounded-md bg-[#f0f4f2] px-2 py-0.5 text-xs font-semibold text-[#65756d]">
          {sessions.length}
        </span>
      </div>

      {sessions.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12 text-center">
            <FolderOpen className="mb-4 h-12 w-12 text-muted-foreground" />
            <h3 className="mb-2 text-lg font-medium">{t('sessions.emptyTitle')}</h3>
            <p className="mb-4 text-muted-foreground">{t('sessions.emptyDescription')}</p>
          
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-3">
          {sortedSessions.map((session) => {
            const editorGate = getEditorGate(session)
            const activeRun = activeRuns[session.id]
            const displayGeneratedCount = activeRun
              ? Math.max(editorGate.generatedCount, activeRun.completedPageCount || 0)
              : editorGate.generatedCount
            const displayFailedCount = activeRun
              ? activeRun.failedPageCount || 0
              : editorGate.failedCount
            const displayTotalCount = activeRun
              ? Math.max(editorGate.totalCount, activeRun.totalPages, displayGeneratedCount + displayFailedCount)
              : editorGate.totalCount
            const hasCompletedPages = editorGate.generatedCount > 0
            const isFullyComplete = canEnterEditor(session) && editorGate.generatedCount >= editorGate.totalCount && editorGate.failedCount === 0
            const isPartialComplete = !isFullyComplete && canEnterEditor(session)
            const isContinuable = !isFullyComplete && !isPartialComplete && hasCompletedPages
            const statusText = activeRun
              ? activeRun.status === 'queued'
                ? t('sessions.statusQueued')
                : activeRun.progress > 0
                  ? t('sessions.statusGeneratingProgress', { progress: activeRun.progress })
                  : t('sessions.statusGenerating')
              : isFullyComplete
              ? t('sessions.statusComplete')
              : isPartialComplete
                ? t('sessions.statusPartialComplete')
                : isContinuable
                  ? t('sessions.statusContinuable')
                  : t('sessions.statusRegenerate')
            const actionText = activeRun
              ? t('sessions.actionViewProgress')
              : isFullyComplete || isPartialComplete
              ? t('sessions.actionEnter')
              : isContinuable
                ? t('sessions.actionContinue')
                : t('sessions.actionRegenerate')
            const sourceTag = getSourceTag(session, {
              pptx: t('sessions.sourcePptx'),
              sessionFile: t('sessions.sourceSessionFile'),
              saveAsNew: t('sessions.sourceSaveAsNew'),
              document: t('sessions.sourceDocument'),
              ai: t('sessions.sourceAi'),
              thinking: t('sessions.sourceThinking'),
              template: t('sessions.sourceTemplate')
            })
            const SourceIcon = sourceTag.Icon
            const sourceTagBaseClass =
              'inline-flex h-7 items-center gap-1.5 rounded-full border px-2.5 text-[11px] font-semibold leading-none'
            const statusClassName = activeRun
              ? 'border-[#b7e6d0]/80 bg-[#eefbf4] text-[#117a51] shadow-[0_0_0_1px_rgba(116,182,229,0.14)]'
              : isFullyComplete
              ? 'border-[#bad8b7]/80 bg-[#eef9ec] text-[#4a7a46]'
              : isPartialComplete
                ? 'border-[#b5c9a8]/80 bg-[#eef5e8] text-[#4f7b3f]'
                : isContinuable
                  ? 'border-[#82c86a]/80 bg-[#e8f8f3] text-[#38702c] shadow-[0_0_0_1px_rgba(130,200,106,0.14)]'
                  : 'border-[#d7b5ae]/70 bg-[#f3e8e6] text-[#93564f]'
            return (
              <Card
                key={session.id}
                className="cursor-pointer transition-all hover:translate-y-[-1px] hover:shadow-[0_14px_28px_rgba(90,72,52,0.16)]"
                title={isPartialComplete ? t('sessions.statusPartialCompleteTip') : undefined}
                onClick={() => navigate(getSessionRoute(session))}
              >
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <CardTitle className="truncate text-base">{session.title}</CardTitle>
                  <div className="flex items-center gap-1">
                    <TooltipProvider delayDuration={180}>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={(e) => {
                              e.stopPropagation()
                              openRenameDialog(session)
                            }}
                          >
                            <Pencil className="h-4 w-4" />
                          </Button>
                        </TooltipTrigger>
                        <TooltipContent side="bottom" align="end">
                          {t('sessions.editTitleTooltip')}
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                    <TooltipProvider delayDuration={180}>
                      <Tooltip>
                        <TooltipTrigger asChild>
                          <span
                            className="inline-flex"
                            onClick={(event) => event.stopPropagation()}
                          >
                            <Button
                              variant="ghost"
                              size="sm"
                              disabled={editorGate.generatedCount <= 0}
                              onClick={(event) => {
                                event.stopPropagation()
                                setSaveTemplateTarget(session)
                              }}
                            >
                              <LayoutTemplate className="h-4 w-4" />
                            </Button>
                          </span>
                        </TooltipTrigger>
                        <TooltipContent side="bottom" align="end">
                          {editorGate.generatedCount <= 0
                            ? t('sessions.saveTemplateTooltipDisabled')
                            : t('sessions.saveTemplateTooltip')}
                        </TooltipContent>
                      </Tooltip>
                    </TooltipProvider>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        setDeleteSessionTarget(session)
                      }}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="flex items-center gap-2 text-xs text-muted-foreground">
                  <span className="soft-pill inline-flex items-center gap-1 rounded-lg px-3 py-1 text-secondary-foreground">
                    <MessageSquare className="h-3 w-3" />
                    {actionText}
                  </span>
                  <span className={`rounded-lg border px-2 py-1 font-semibold ${statusClassName}`}>
                    {statusText}
                  </span>
                  <span className={`${sourceTagBaseClass} ${sourceTag.className}`}>
                    <SourceIcon className={`h-3.5 w-3.5 ${sourceTag.iconClassName}`} />
                    {sourceTag.label}
                  </span>
                  <span className="rounded-lg border border-[#b5c4a1]/80 bg-[#e8f8f3]/75 px-2 py-1 text-[#5d6b4d]">
                    {t('sessions.pagesCount', { generated: displayGeneratedCount, total: displayTotalCount })}
                  </span>
                  {session.generation_duration_sec ? (
                    <span className="rounded-lg border border-[#c8d6ba]/60 bg-[#f0faf5] px-2 py-1 text-[#6b6560]">
                      {(() => {
                        const d = dayjs.duration(session.generation_duration_sec!, 'second')
                        const m = Math.floor(d.asMinutes())
                        const s = d.seconds()
                        return m > 0 ? `${m}m ${s}s` : `${s}s`
                      })()}
                    </span>
                  ) : null}
                  <span className="rounded-lg border border-[#c8d6ba]/60 bg-[#f0faf5] px-2 py-1 text-[#6b6560]">
                    {dayjs.unix(session.updated_at).format('YYYY/MM/DD HH:mm')}
                  </span>
                  {!isFullyComplete && displayFailedCount > 0 && (
                    <span className="rounded-lg border border-[#d7b5ae]/70 bg-[#f3e8e6]/80 px-2 py-1 text-[#93564f]">
                      {t('sessions.failedCount', { count: displayFailedCount })}
                    </span>
                  )}
                </div>
              </CardContent>
            </Card>
            )
          })}
        </div>
      )}
      {renameSession ? (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-[#1f261d]/35 p-4 backdrop-blur-sm"
          onClick={closeRenameDialog}
        >
          <div
            className="w-full max-w-md rounded-xl border border-[#b5c4a1]/80 bg-[#e8f8f3] p-5 shadow-[0_24px_60px_rgba(64,52,38,0.28)]"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="mb-4 flex items-start justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold text-[#3e4a32]">{t('sessions.editTitle')}</h2>
                <p className="mt-1 text-xs text-muted-foreground">
                  {t('sessions.renameDescription')}
                </p>
              </div>
              <Button variant="ghost" size="sm" onClick={closeRenameDialog} disabled={renaming}>
                <X className="h-4 w-4" />
              </Button>
            </div>
            <form
              className="space-y-4"
              onSubmit={(event) => {
                event.preventDefault()
                void handleRenameSubmit()
              }}
            >
              <Input
                autoFocus
                value={renameTitle}
                maxLength={120}
                placeholder={t('sessions.renamePlaceholder')}
                onChange={(event) => setRenameTitle(event.target.value)}
              />
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" size="sm" onClick={closeRenameDialog} disabled={renaming}>
                  {t('common.cancel')}
                </Button>
                <Button type="submit" size="sm" disabled={renaming}>
                  {renaming ? t('common.saving') : t('common.save')}
                </Button>
              </div>
            </form>
          </div>
        </div>
      ) : null}
      <Dialog open={Boolean(deleteSessionTarget)} onOpenChange={(open) => !open && closeDeleteDialog()}>
        <DialogContent showClose={false}>
          <DialogHeader>
            <DialogTitle>{t('sessions.deleteConfirmTitle')}</DialogTitle>
            <DialogDescription>
              {t('sessions.deleteConfirmDescription', { title: deleteSessionTarget?.title || '' })}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button type="button" variant="outline" size="sm" onClick={closeDeleteDialog} disabled={deleting}>
              {t('common.cancel')}
            </Button>
            <Button type="button" size="sm" onClick={() => void handleDeleteSession()} disabled={deleting}>
              {deleting ? t('common.saving') : t('common.delete')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
      <SaveTemplateDialog
        open={Boolean(saveTemplateTarget)}
        defaultName={saveTemplateTarget?.title || ''}
        saving={savingTemplate}
        onOpenChange={(open) => !open && setSaveTemplateTarget(null)}
        onSubmit={(payload) => void handleSaveTemplate(payload)}
      />
    </div>
  )
}
