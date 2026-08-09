import { Copy, Trash2 } from 'lucide-react'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogTitle,
  AlertDialogTrigger
} from '../../ui/AlertDialog'
import { useT } from '@renderer/i18n'

export function InspectorActions({
  onCopy,
  onDelete
}: {
  onCopy?: () => void
  onDelete?: () => void
}): React.JSX.Element {
  const t = useT()
  return (
    <div className="flex gap-2 px-0.5 pb-1 pt-1">
      {onCopy && (
        <button
          type="button"
          className="flex h-8 flex-1 items-center justify-center gap-1.5 rounded-full border border-[#c8d6ba]/40 bg-[#f0faf5]/60 text-xs font-medium text-[#59664b] transition-colors hover:bg-[#d4e4c1]/60"
          onClick={onCopy}
        >
          <Copy className="h-3.5 w-3.5" />
          {t('sessionDetail.copyElement')}
        </button>
      )}
      {onDelete && (
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <button
              type="button"
              className="flex h-8 flex-1 items-center justify-center gap-1.5 rounded-full border border-[#e8c8c6]/80 bg-[#f0faf5]/60 text-xs font-medium text-[#8e5a53] transition-colors hover:border-[#c0392b]/40 hover:bg-[#fdf0ef] hover:shadow-[0_4px_12px_rgba(192,57,43,0.1)]"
            >
              <Trash2 className="h-3.5 w-3.5" />
              {t('sessionDetail.deleteElement')}
            </button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogTitle>{t('sessionDetail.deleteElement')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('sessionDetail.deleteElementConfirm')}
            </AlertDialogDescription>
            <div className="flex justify-end gap-2">
              <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
              <AlertDialogAction
                className="bg-[#c0392b] text-white hover:bg-[#a93226]"
                onClick={onDelete}
              >
                {t('common.delete')}
              </AlertDialogAction>
            </div>
          </AlertDialogContent>
        </AlertDialog>
      )}
    </div>
  )
}
