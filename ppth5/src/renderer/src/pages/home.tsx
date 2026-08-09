import { useCallback, type ReactElement } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowRight, FileText } from 'lucide-react'
import { useT } from '../i18n'
import { useModelAction } from '../hooks/useModelAction'

export function HomePage(): ReactElement {
  const navigate = useNavigate()
  const { ensureModelActive } = useModelAction()
  const t = useT()

  const handleQuickCreate = useCallback(async () => {
    if (!(await ensureModelActive())) return
    navigate('/create/session')
  }, [ensureModelActive, navigate])

  return (
    <div className="mx-auto flex min-h-[calc(100vh-5rem)] w-full max-w-6xl items-center justify-center px-6 py-9 text-[#24342d] lg:px-8">
      <section className="flex w-full justify-center">
        <button
          type="button"
          onClick={() => void handleQuickCreate()}
          className="group relative flex min-h-[240px] w-full max-w-2xl flex-col overflow-hidden rounded-2xl border border-[#dcebe8] bg-white/88 p-7 text-left shadow-[0_14px_34px_rgba(17,122,81,0.08)] transition-colors hover:border-[#b7e6d0] hover:bg-[#f4fff9]"
        >
          <div className="relative flex items-start justify-between gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-[#dff8eb] text-[#21b978] shadow-[0_10px_22px_rgba(33,185,120,0.10)]">
              <FileText className="h-5 w-5" />
            </div>
            <span className="rounded-full bg-[#eefbf4] px-3 py-1.5 text-[11px] font-semibold text-[#117a51]">
              {t('thinking.quickCreateBadge')}
            </span>
          </div>

          <div className="relative mt-7">
            <h2 className="text-[28px] font-semibold leading-tight text-[#24342d]">
              {t('thinking.quickCreate')}
            </h2>
            <p className="mt-3 max-w-[32rem] text-[14px] leading-relaxed text-[#65756d]">
              {t('thinking.quickCreateDescription')}
            </p>
          </div>

          <div className="relative mt-auto pt-7">
            <span className="inline-flex h-10 items-center gap-2 rounded-lg bg-[#21b978] px-5 text-[13px] font-semibold text-white shadow-[0_10px_22px_rgba(33,185,120,0.18)] transition-colors group-hover:bg-[#117a51]">
              {t('thinking.startQuickCreate')}
              <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
            </span>
          </div>
        </button>
      </section>
    </div>
  )
}
