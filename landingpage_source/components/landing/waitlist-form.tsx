'use client'

import { ArrowRight } from 'lucide-react'

const PT_APP_URL = process.env.NEXT_PUBLIC_PT_APP_URL ?? ''

export function WaitlistForm({ dark = false }: { source?: string; dark?: boolean }) {
  return (
    <a
      href={`${PT_APP_URL}/pt/signup/`}
      className={[
        'inline-flex h-12 items-center gap-2 rounded-xl px-6 text-[15px] font-semibold transition active:scale-[0.98]',
        dark
          ? 'bg-white text-slate-900 hover:bg-slate-100 shadow-[0_8px_24px_-8px_rgba(255,255,255,0.3)]'
          : 'bg-[#14B8A6] text-white hover:bg-[#0D9488] shadow-[0_8px_24px_-8px_rgba(20,184,166,0.6)]',
      ].join(' ')}
    >
      Get Early Access
      <ArrowRight size={17} className="transition-transform group-hover:translate-x-0.5" />
    </a>
  )
}
