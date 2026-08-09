import { cn } from '@renderer/lib/utils'
import { Home, FolderOpen, ArrowLeft, Presentation } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import { useT } from '@renderer/i18n'

export function Sidebar(): React.JSX.Element {
  const location = useLocation()
  const t = useT()
  const isDetailPage = location.pathname.startsWith('/sessions/') && location.pathname !== '/sessions'

  const navItems = [
    { path: '/', icon: Home, label: t('nav.home') },
    { path: '/sessions', icon: FolderOpen, label: t('nav.sessions') }
  ]

  return (
    <aside className="flex h-full w-full flex-col bg-transparent">
      <div className="px-4 pt-3">
        <div className="flex items-center gap-3">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-[#b7e6d0] bg-[#e8f8ef] text-[#21b978] shadow-[0_8px_20px_rgba(33,185,120,0.12)]">
            <Presentation className="h-5 w-5" />
          </span>
          <h1 className="truncate text-[20px] font-semibold leading-none text-[#24342d]">Oh My PPT</h1>
        </div>
        <p className="mt-2 px-0.5 text-[13px] text-[#65756d]">{t('nav.tagline')}</p>
      </div>

      <nav className="flex-1 space-y-1 px-3 pb-4 pt-6">
        {isDetailPage && (
          <Link
            to="/sessions"
            className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-[#475569] transition-colors hover:bg-[#f1f8f8]"
          >
            <ArrowLeft className="w-4 h-4" />
            {t('nav.backToSessions')}
          </Link>
        )}
        {navItems.map((item) => {
          const isActive = item.path === '/' ? location.pathname === '/' : location.pathname.startsWith(item.path)
          return (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors',
                isActive
                  ? 'bg-[#f1f8f8] text-[#117a51]'
                  : 'text-[#475569] hover:bg-[#f1f8f8] hover:text-[#24342d]'
              )}
            >
              <item.icon className="w-4 h-4" />
              {item.label}
            </Link>
          )
        })}
      </nav>

    </aside>
  )
}
