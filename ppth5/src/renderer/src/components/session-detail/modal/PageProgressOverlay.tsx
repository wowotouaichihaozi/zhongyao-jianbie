import { useT, type I18nKey } from '@renderer/i18n'
import { useGenerateStore, useSessionDetailUiStore } from '@renderer/store'

type PageProgressVariant = 'add' | 'retry'

interface SingleProgressOverlayProps {
  variant: PageProgressVariant
  label?: string
  progress?: number
}

const variantStyles: Record<
  PageProgressVariant,
  { spinnerBorder: string; spinnerTop: string; text: string; fill: string; fallbackKey: I18nKey }
> = {
  add: {
    spinnerBorder: 'border-[#d4e4c1]',
    spinnerTop: 'border-t-[#5d6b4d]',
    text: 'text-[#3e4a32]',
    fill: 'bg-[#5d6b4d]',
    fallbackKey: 'sessionDetail.addPageGenerating'
  },
  retry: {
    spinnerBorder: 'border-[#f3e4df]',
    spinnerTop: 'border-t-[#93564f]',
    text: 'text-[#93564f]',
    fill: 'bg-[#93564f]',
    fallbackKey: 'sessionDetail.retryPageGenerating'
  }
}

function SingleProgressOverlay({
  open,
  variant,
  label,
  progress
}: SingleProgressOverlayProps & { open: boolean }): React.JSX.Element | null {
  const t = useT()
  const styles = variantStyles[variant]

  if (!open) return null

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="flex w-[360px] flex-col items-center gap-4 rounded-2xl bg-white/95 px-8 py-6 shadow-2xl">
        <div
          className={`h-6 w-6 animate-spin rounded-full border-2 ${styles.spinnerBorder} ${styles.spinnerTop}`}
        />
        <div className="flex w-full flex-col items-center gap-2">
          <p className={`text-sm font-medium ${styles.text}`}>{label || t(styles.fallbackKey)}</p>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-[#d4e4c1]">
            <div
              className={`h-full rounded-full transition-all duration-300 ease-out ${styles.fill}`}
              style={{ width: `${Math.min(100, Math.max(0, progress ?? 0))}%` }}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

export function PageProgressOverlay(): React.JSX.Element {
  const isAddingPage = useSessionDetailUiStore((state) => state.isAddingPage)
  const isRetryingSinglePage = useSessionDetailUiStore((state) => state.isRetryingSinglePage)
  const progress = useGenerateStore((state) => state.progress)

  return (
    <>
      <SingleProgressOverlay
        open={isAddingPage}
        variant="add"
        label={progress?.label}
        progress={progress?.progress}
      />
      <SingleProgressOverlay
        open={isRetryingSinglePage}
        variant="retry"
        label={progress?.label}
        progress={progress?.progress}
      />
    </>
  )
}
