import {
  CopyPlus,
  FileSearch,
  Globe,
  History,
  Home,
  LayoutTemplate,
  Loader2,
  Monitor,
  MoreHorizontal,
  Presentation
} from 'lucide-react'
import { cn } from '@renderer/lib/utils'
import { useSessionDetailRuntimeStore, useSessionDetailUiStore } from '@renderer/store'
import { Button } from '../../ui/Button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from '../../ui/DropdownMenu'
import { Tooltip, TooltipContent, TooltipTrigger } from '../../ui/Tooltip'
import { useT } from '@renderer/i18n'
import { SaveTemplateDialog } from '../../templates/SaveTemplateDialog'
import { SaveAsNewSessionDialog } from './SaveAsNewSessionDialog'
import { useSessionToolbarController } from './useSessionToolbarController'

const btnClass =
  'h-7 rounded-[8px] border-transparent bg-[#d4e4c1]/72 px-2.5 text-[11px] text-[#3e4a32] shadow-[0_4px_10px_rgba(86,72,53,0.08)] hover:bg-[#d4e4c1]/78'
const iconClass = 'mr-1.5 h-3.5 w-3.5'
const dropIconClass = 'mr-2 h-3.5 w-3.5 text-[#6b7280]'

const isMac = window.electron?.process?.platform === 'darwin'

export function SessionToolbar({
  sessionId,
  isSavingEdits
}: {
  sessionId: string
  isSavingEdits?: boolean
}): React.JSX.Element {
  const t = useT()
  const {
    hasPages,
    isGenerating,
    historyDisabled,
    canPreview,
    canRevealFile,
    sessionTitle,
    saveTemplateOpen,
    savingTemplate,
    saveAsNewSessionOpen,
    savingAsNewSession,
    saveAsNewSessionDisabled,
    defaultTemplateName,
    defaultSaveAsNewSessionName,
    setSaveTemplateOpen,
    setSaveAsNewSessionOpen,
    handleSaveTemplate,
    handleSaveAsNewSession,
    exportActions,
    openHistory
  } = useSessionToolbarController(sessionId)

  const ribbonActions = useSessionDetailRuntimeStore((state) => state.workspaceRibbonActions)

  const isExportingPdf = useSessionDetailUiStore((state) => state.isExportingPdf)
  const isExportingPng = useSessionDetailUiStore((state) => state.isExportingPng)
  const isExportingPptx = useSessionDetailUiStore((state) => state.isExportingPptx)
  const isExportingSlidePack = useSessionDetailUiStore((state) => state.isExportingSlidePack)
  const isExportingSessionZip = useSessionDetailUiStore((state) => state.isExportingSessionZip)
  const isExporting =
    isExportingPdf ||
    isExportingPng ||
    isExportingPptx ||
    isExportingSlidePack ||
    isExportingSessionZip

  const exportingAny = isExporting
  const homeDisabled = exportingAny || isGenerating || !!isSavingEdits

  return (
    <>
      {/* Mac left padding for traffic lights */}
      <div className={cn('flex h-full items-center gap-2', isMac ? 'pl-[85px]' : 'pl-4')}>
        {/* Home / Back */}
        <Tooltip>
          <TooltipTrigger asChild>
            <button
              type="button"
              className="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-[8px] bg-[#d4e4c1]/72 text-[#3e4a32] shadow-[0_4px_10px_rgba(86,72,53,0.08)] transition-colors hover:bg-[#d4e4c1]/78 disabled:pointer-events-none disabled:opacity-45"
              onClick={() => ribbonActions?.onBackToSessions()}
              disabled={homeDisabled}
            >
              <Home className="h-3.5 w-3.5" />
            </button>
          </TooltipTrigger>
          <TooltipContent side="bottom">{t('sessionDetail.backToSessions')}</TooltipContent>
        </Tooltip>

        {/* Title */}
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="flex w-[150px] shrink-0 items-center gap-2 rounded-[10px] bg-[#d4e4c1]/60 px-3 py-1">
              <div className="min-w-0 flex-1 truncate text-[12px] font-medium text-[#3e4a32]">
                {sessionTitle}
              </div>
            </div>
          </TooltipTrigger>
          <TooltipContent side="bottom" align="start">
            {sessionTitle}
          </TooltipContent>
        </Tooltip>

        {/* Editable PPTX export */}
        {hasPages && (
          <Button
            type="button"
            variant="outline"
            size="sm"
            className={btnClass}
            disabled={exportingAny}
            onClick={() => void exportActions.exportPptx()}
          >
            {exportingAny ? (
              <Loader2 className={cn(iconClass, 'animate-spin')} />
            ) : (
              <Presentation className={iconClass} />
            )}
            {t('sessionDetail.toolbarExportPptxEditable')}
          </Button>
        )}

        {/* Browse */}
        {canPreview && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className={btnClass}
                onClick={() => void exportActions.openProjectPreview()}
                disabled={exportingAny}
              >
                <Globe className={iconClass} />
                {t('sessionDetail.preview')}
              </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom" align="start">
              {t('sessionDetail.previewTooltip')}
            </TooltipContent>
          </Tooltip>
        )}

        {/* Present */}
        {hasPages && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className={btnClass}
                onClick={() => void exportActions.openPresentation()}
                disabled={exportingAny}
              >
                <Monitor className={iconClass} />
                {t('sessionDetail.present')}
              </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom" align="start">
              {t('sessionDetail.presentTooltip')}
            </TooltipContent>
          </Tooltip>
        )}

        {/* Version History */}
        {hasPages && (
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className={btnClass}
                onClick={openHistory}
                disabled={historyDisabled || exportingAny}
              >
                <History className={iconClass} />
                {t('sessionDetail.history')}
              </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom" align="start">
              {t('sessionDetail.historyTooltip')}
            </TooltipContent>
          </Tooltip>
        )}

        {/* More dropdown */}
        {hasPages && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className={cn(btnClass, 'px-2')}
                disabled={exportingAny}
              >
                <MoreHorizontal className="h-3.5 w-3.5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="min-w-[12rem]">
              <DropdownMenuItem
                disabled={saveAsNewSessionDisabled || !!isSavingEdits}
                onClick={() => setSaveAsNewSessionOpen(true)}
              >
                {savingAsNewSession ? (
                  <Loader2 className={cn(dropIconClass, 'animate-spin')} />
                ) : (
                  <CopyPlus className={dropIconClass} />
                )}
                {t('sessionDetail.saveAsNewSession')}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => setSaveTemplateOpen(true)}>
                <LayoutTemplate className={dropIconClass} />
                {t('sessionDetail.saveTemplate')}
              </DropdownMenuItem>
              {canRevealFile && (
                <DropdownMenuItem onClick={() => void exportActions.revealSelectedPageFile()}>
                  <FileSearch className={dropIconClass} />
                  {t('sessionDetail.revealFile')}
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        )}
      </div>

      <SaveTemplateDialog
        open={saveTemplateOpen}
        defaultName={defaultTemplateName}
        saving={savingTemplate}
        onOpenChange={setSaveTemplateOpen}
        onSubmit={(payload) => void handleSaveTemplate(payload)}
      />
      <SaveAsNewSessionDialog
        open={saveAsNewSessionOpen}
        defaultName={defaultSaveAsNewSessionName}
        saving={savingAsNewSession}
        onOpenChange={setSaveAsNewSessionOpen}
        onSubmit={(payload) => void handleSaveAsNewSession(payload)}
      />
    </>
  )
}
