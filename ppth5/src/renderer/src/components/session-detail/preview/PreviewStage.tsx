import { useCallback, useEffect, forwardRef, useRef } from 'react'
import { Loader2, Sparkles } from 'lucide-react'
import { useSessionDetailUiStore } from '@renderer/store'
import { PreviewIframe, type PreviewIframeHandle } from '../../preview/PreviewIframe'
import type { EditModeMovePayload, EditSelectionPayload } from '../../preview/edit-mode-script'
import type { SessionPreviewPage } from '../shared/types'
import { useT } from '@renderer/i18n'

export const PreviewStage = forwardRef<
  PreviewIframeHandle,
  {
    selectedPage: SessionPreviewPage | null
    sessionTitle?: string | null
    isGenerating: boolean
    progressLabel?: string
    previewRefreshKey?: number
    onElementMoved: (payload: EditModeMovePayload) => void
    onElementSelected: (payload: EditSelectionPayload) => void
    onCancelElementEdit: () => void
    onDiscardAllEdits: () => void
    onUndo: () => void
    onRedo: () => void
    onReplayPendingEdits: () => void
    onDeleteRequest?: (selector: string) => void
  }
>(function PreviewStage(
  {
    selectedPage,
    isGenerating,
    progressLabel,
    previewRefreshKey = 0,
    onElementMoved,
    onElementSelected,
    onCancelElementEdit,
    onDiscardAllEdits,
    onUndo,
    onRedo,
    onReplayPendingEdits,
    onDeleteRequest
  },
  ref
) {
  const t = useT()
  const previewIframeRef = useRef<PreviewIframeHandle>(null)
  const wasEditingRef = useRef(false)
  const previewIdentityRef = useRef('')
  const restoreTimerRef = useRef<number | null>(null)
  const previewKey = useSessionDetailUiStore((state) => state.previewKey)
  const interactionMode = useSessionDetailUiStore((state) => state.interactionMode)
  const setInteractionMode = useSessionDetailUiStore((state) => state.setInteractionMode)
  const setWorkspaceTab = useSessionDetailUiStore((state) => state.setWorkspaceTab)
  const editSelectedSelector = useSessionDetailUiStore((state) => state.editSelectedSelector)
  const setSelectedElement = useSessionDetailUiStore((state) => state.setSelectedElement)
  const isEditing = interactionMode === 'edit'
  const isInspecting = interactionMode === 'ai-inspect'

  const setPreviewIframeHandle = useCallback(
    (handle: PreviewIframeHandle | null): void => {
      previewIframeRef.current = handle
      if (typeof ref === 'function') {
        ref(handle)
        return
      }
      if (ref) {
        ref.current = handle
      }
    },
    [ref]
  )

  const restoreEditSelection = useCallback(
    (selector: string): void => {
      if (restoreTimerRef.current !== null) {
        window.clearTimeout(restoreTimerRef.current)
        restoreTimerRef.current = null
      }

      let attempts = 0
      const tryRestore = (): void => {
        attempts += 1
        window.requestAnimationFrame(() => {
          const restorePromise = previewIframeRef.current?.restoreEditModeSelection(selector)
          void restorePromise?.then((restored) => {
            if (restored || attempts >= 3) return
            restoreTimerRef.current = window.setTimeout(tryRestore, 50)
          })
        })
      }

      restoreTimerRef.current = window.setTimeout(tryRestore, 0)
    },
    []
  )

  useEffect(() => {
    return () => {
      if (restoreTimerRef.current !== null) {
        window.clearTimeout(restoreTimerRef.current)
        restoreTimerRef.current = null
      }
    }
  }, [])

  const handleDidReload = useCallback((): void => {
    onReplayPendingEdits()
    if (!isEditing || !editSelectedSelector) return
    restoreEditSelection(editSelectedSelector)
  }, [editSelectedSelector, isEditing, onReplayPendingEdits, restoreEditSelection])

  useEffect(() => {
    const previewIdentity = `${selectedPage?.pageId || ''}:${previewKey}:${previewRefreshKey}`
    const enteredEditMode = isEditing && !wasEditingRef.current
    const previewChangedWhileEditing = isEditing && previewIdentity !== previewIdentityRef.current

    wasEditingRef.current = isEditing
    previewIdentityRef.current = previewIdentity

    if (!isEditing || !editSelectedSelector) return
    if (!enteredEditMode && !previewChangedWhileEditing) return

    restoreEditSelection(editSelectedSelector)
    return () => {
      if (restoreTimerRef.current !== null) {
        window.clearTimeout(restoreTimerRef.current)
        restoreTimerRef.current = null
      }
    }
  }, [
    editSelectedSelector,
    isEditing,
    restoreEditSelection,
    selectedPage?.pageId,
    previewKey,
    previewRefreshKey
  ])

  useEffect(() => {
    if (interactionMode === 'preview') return
    const onKeyDown = (event: KeyboardEvent): void => {
      const target = event.target
      const isEditableTarget =
        target instanceof Element &&
        Boolean(
          target.closest('input, textarea, select, [contenteditable="true"], [contenteditable=""]')
        )
      if (isEditing && !isEditableTarget && (event.metaKey || event.ctrlKey)) {
        const key = event.key.toLowerCase()
        if (key === 'z') {
          event.preventDefault()
          if (event.shiftKey) onRedo()
          else onUndo()
          return
        }
        if (key === 'y') {
          event.preventDefault()
          onRedo()
          return
        }
      }
      if (event.key === 'Escape') {
        if (isEditing) {
          onDiscardAllEdits()
        } else {
          setInteractionMode('preview')
          setWorkspaceTab('preview')
          onCancelElementEdit()
        }
      }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [
    interactionMode,
    isEditing,
    onDiscardAllEdits,
    onCancelElementEdit,
    onUndo,
    onRedo,
    setInteractionMode,
    setWorkspaceTab
  ])

  return (
    <main className="flex min-h-0 flex-1 flex-col px-3 pb-3 pt-1">
      <div className="relative min-h-0 flex-1 overflow-hidden rounded-2xl bg-[#dff8eb]/72 p-3 shadow-[0_18px_38px_rgba(17,122,81,0.08)]">
        {selectedPage ? (
          <div className="relative h-full overflow-hidden rounded-xl bg-white p-2 shadow-[0_10px_24px_rgba(17,122,81,0.08)]">
            <PreviewIframe
              ref={setPreviewIframeHandle}
              key={`preview-${selectedPage.pageId}-${previewKey}-${previewRefreshKey}`}
              src={selectedPage.sourceUrl}
              htmlPath={selectedPage.htmlPath}
              pageId={selectedPage.pageId}
              title={`preview-page-${selectedPage.pageNumber}`}
              inspectable
              interactionMode={interactionMode}
              inspecting={isInspecting}
              editMode={isEditing}
              onSelectorSelected={setSelectedElement}
              onElementMoved={onElementMoved}
              onElementSelected={onElementSelected}
              onInspectExit={() => {
                setInteractionMode('preview')
                setWorkspaceTab('preview')
                onCancelElementEdit()
              }}
              onDidReload={handleDidReload}
              onDeleteRequest={onDeleteRequest}
            />
            {selectedPage.status === 'failed' && (
              <div className="absolute bottom-5 left-5 z-20 max-w-[520px] rounded-[1rem] bg-[#f3e8e6]/92 px-3 py-2 text-xs text-[#8e5a53] shadow-[0_10px_24px_rgba(142,90,83,0.12)] backdrop-blur-sm">
                {t('sessionDetail.failedPageHint')}
              </div>
            )}
            {isGenerating && (
              <div className="absolute inset-0 flex items-center justify-center rounded-xl bg-white/68 backdrop-blur-sm transition-opacity">
                <div className="flex flex-col items-center gap-3 rounded-xl bg-[#dff8eb]/92 px-8 py-5 shadow-[0_14px_30px_rgba(31,124,125,0.1)]">
                  <Loader2 className="h-6 w-6 animate-spin text-[#21b978]" />
                  {progressLabel ? <p className="text-sm text-[#365b56]">{progressLabel}</p> : null}
                </div>
              </div>
            )}
          </div>
        ) : (
          <div className="relative flex h-full min-h-[420px] flex-col items-center justify-center gap-4 rounded-xl bg-white/86 text-center text-[#65756d] shadow-[inset_0_0_0_1px_rgba(31,188,190,0.10)]">
            {isGenerating ? (
              <Loader2 className="h-7 w-7 animate-spin text-[#21b978]" />
            ) : (
              <Sparkles className="h-7 w-7 text-[#21b978]" />
            )}
            <div className="space-y-1">
              <p className="text-base font-medium text-[#24342d]">
                {t('sessionDetail.emptyPreviewTitle')}
              </p>
              <p className="text-sm">
                {isGenerating ? t('sessionDetail.preparingPreview') : t('sessionDetail.briefHint')}
              </p>
            </div>
          </div>
        )}
      </div>
    </main>
  )
})
