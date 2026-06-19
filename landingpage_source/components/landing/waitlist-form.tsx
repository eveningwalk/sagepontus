'use client'

import { useState } from 'react'
import { ArrowRight, Check } from 'lucide-react'

const isEmail = (v: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim())

type State = 'idle' | 'loading' | 'error' | 'done'

export function WaitlistForm({ source = 'landing', dark = false }: { source?: string; dark?: boolean }) {
  const [email, setEmail]   = useState('')
  const [state, setState]   = useState<State>('idle')
  const [errMsg, setErrMsg] = useState('')

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isEmail(email)) { setErrMsg('Please enter a valid work email.'); setState('error'); return }

    setState('loading')
    try {
      const url = process.env.NEXT_PUBLIC_WAITLIST_URL ?? '/api/waitlist'
      const res = await fetch(url, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ email: email.trim().toLowerCase(), source }),
      })
      const data = await res.json()
      if (!res.ok) { setErrMsg(data.error || 'Something went wrong.'); setState('error'); return }
      if (typeof window !== 'undefined' && typeof (window as any).lintrk === 'function') {
        const convId = process.env.NEXT_PUBLIC_LINKEDIN_CONVERSION_ID
        if (convId) (window as any).lintrk('track', { conversion_id: Number(convId) })
      }
      setState('done')
    } catch {
      setErrMsg('Network error — please try again.'); setState('error')
    }
  }

  if (state === 'done') {
    return (
      <div className={`pop-in inline-flex items-center gap-3 rounded-xl border px-4 py-3 ${dark ? 'border-white/25 bg-white/10' : 'border-[#14B8A6]/30 bg-[#14B8A6]/8'}`}>
        <span className={`grid h-7 w-7 place-items-center rounded-full ${dark ? 'bg-white text-slate-900' : 'bg-[#14B8A6] text-white'}`}>
          <Check size={16} strokeWidth={3} />
        </span>
        <div className="text-left">
          <div className={`text-[15px] font-semibold ${dark ? 'text-white' : 'text-[#0F172A]'}`}>You're on the list — check your inbox!</div>
          <div className={`text-[13px] ${dark ? 'text-white/80' : 'text-[#64748B]'}`}>Confirmation sent to {email.toLowerCase()}</div>
        </div>
      </div>
    )
  }

  return (
    <form onSubmit={submit} className="w-full">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <input
            type="email"
            value={email}
            onChange={(e) => { setEmail(e.target.value); if (state === 'error') { setState('idle'); setErrMsg('') } }}
            placeholder="you@clinic.com"
            disabled={state === 'loading'}
            className={[
              'h-12 w-full rounded-xl border px-4 text-[15px] outline-none transition disabled:opacity-60',
              dark
                ? 'border-white/20 bg-white/10 text-white placeholder:text-white/60 focus:border-white/50 focus:ring-4 focus:ring-white/20'
                : 'bg-white text-[#0F172A] placeholder:text-[#94A3B8]',
              !dark && (state === 'error'
                ? 'border-red-400 ring-2 ring-red-100'
                : 'border-[#E2E8F0] focus:border-[#14B8A6] focus:ring-2 focus:ring-[#14B8A6]/15'),
            ].join(' ')}
          />
        </div>
        <button
          type="submit"
          disabled={state === 'loading'}
          className="group inline-flex h-12 items-center justify-center gap-2 rounded-xl bg-[#14B8A6] px-5 text-[15px] font-semibold text-white shadow-[0_8px_24px_-8px_rgba(20,184,166,0.6)] transition hover:bg-[#0D9488] active:scale-[0.98] disabled:opacity-60"
        >
          {state === 'loading' ? (
            <span className="spin inline-block h-4 w-4 rounded-full border-2 border-white/30 border-t-white" />
          ) : (
            <>
              Join the Waitlist
              <ArrowRight size={17} className="transition-transform group-hover:translate-x-0.5" />
            </>
          )}
        </button>
      </div>
      <div className={`mt-2 h-4 text-[13px] ${dark ? 'text-rose-200' : 'text-red-500'}`}>{errMsg}</div>
    </form>
  )
}
