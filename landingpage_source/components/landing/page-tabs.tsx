'use client'

import { useState } from 'react'
import { AuthorityPage } from './authority-page'
import { SeoPage } from './seo-page'

interface Props {
  children: React.ReactNode
}

type Tab = 'original' | 'authority' | 'seo'

const descriptors: Record<Tab, string> = {
  original: 'Centered hero · inline form',
  authority: 'Split hero · sticky bar CTA on scroll ↓',
  seo: 'Semantic HTML · cite / blockquote / aria-hidden',
}

const isDev = process.env.NODE_ENV === 'development'

export function PageTabs({ children }: Props) {
  // Production: SEO page only, no tab UI
  if (!isDev) return <SeoPage />

  // Dev: full tab switcher, defaulting to seo
  const [tab, setTab] = useState<Tab>('seo')

  function switchTo(next: Tab) {
    setTab(next)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <>
      {/* ── Tab switcher — fixed top-right, dev only ─────────── */}
      <div className="fixed top-3 right-4 z-50 flex flex-col items-end gap-1.5">
        <div className="flex items-center gap-1 rounded-full border border-slate-200/80 bg-white/90 backdrop-blur-md p-1 shadow-[0_8px_24px_-10px_rgba(15,23,42,.25)]">
          {(['original', 'authority', 'seo'] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => switchTo(t)}
              className={`px-3.5 py-1.5 rounded-full text-[12px] font-semibold transition capitalize ${
                tab === t
                  ? 'bg-slate-900 text-white shadow-sm'
                  : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              {t === 'authority' ? 'Authority ✦' : t === 'seo' ? 'SEO ✦' : 'Original'}
            </button>
          ))}
        </div>

        {/* flow descriptor */}
        <p className="rounded-full bg-slate-900/80 px-2.5 py-0.5 text-[10px] font-medium text-white/85 backdrop-blur-md shadow-sm">
          {descriptors[tab]}
        </p>
      </div>

      {/* ── Content ──────────────────────────────────────────────── */}
      {tab === 'original' && children}
      {tab === 'authority' && <AuthorityPage />}
      {tab === 'seo' && <SeoPage />}
    </>
  )
}
