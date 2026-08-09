import { useEffect, useState } from 'react'
import { cn } from '@renderer/lib/utils'
import { useWorkspaceRibbonController } from '../hooks/useWorkspaceRibbonController'
import { DynamicToolRow } from './toolbar/DynamicToolRow'
import { PrimaryActions } from './toolbar/PrimaryActions'
import { WorkspaceTabs } from './toolbar/WorkspaceTabs'

export function WorkspaceRibbon({
  isSavingEdits
}: {
  isSavingEdits: boolean
}): React.JSX.Element | null {
  const [isPreviewSettling, setIsPreviewSettling] = useState(false)
  const { selectedPageKey, state, activateTab } = useWorkspaceRibbonController(isSavingEdits)

  useEffect(() => {
    if (!selectedPageKey) {
      setIsPreviewSettling(false)
      return
    }
    setIsPreviewSettling(true)
    const timer = window.setTimeout(() => {
      setIsPreviewSettling(false)
    }, 500)
    return () => window.clearTimeout(timer)
  }, [selectedPageKey])

  if (!selectedPageKey) return null

  const toolbarDisabled = state.isGenerating || state.isSavingEdits || isPreviewSettling

  return (
    <div
      className={cn(
        'flex min-w-0 flex-col gap-1 px-3 pb-1.5 pt-1 transition-opacity duration-200',
        isPreviewSettling && 'pointer-events-none opacity-0'
      )}
    >
      <div className="actions-tool flex min-w-0 items-center gap-2 px-1.5 py-0.5">
        <PrimaryActions
          disabled={toolbarDisabled}
          isSavingEdits={state.isSavingEdits}
          canUndo={state.canUndo}
          canRedo={state.canRedo}
          hasPendingEdits={state.hasPendingEdits}
        />
        <WorkspaceTabs
          activeTab={state.activeTab}
          disabled={toolbarDisabled}
          onActivate={activateTab}
        />
      </div>

      <DynamicToolRow state={state} disabled={toolbarDisabled} />
    </div>
  )
}
