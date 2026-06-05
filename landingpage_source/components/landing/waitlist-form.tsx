'use client'

import { useState } from 'react'
import { ArrowRight, Check } from 'lucide-react'

const isEmail = (v: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim())

type State = 'idle' | 'loading' | 'error' | 'done'

export function WaitlistForm({ source = 'landing' }: { source?: string }) {
  const [email, setEmail]   = useState('')
  const [state, setState]   = useState<State>('idle')
  const [errMsg, setErrMsg] = useState('')

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!isEmail(email)) { setErrMsg('Please enter a valid work email.'); setState('error'); return }

    setState('loading')
    try {
      const res = await fetch('/api/waitlist', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ email: email.trim().toLowerCase(), source }),
      })
      const data = await res.json()
      if (!res.ok) { setErrMsg(data.error || 'Something went wrong.'); setState('error'); return }
      setState('done')
    } catch {
      setErrMsg('Network error — please try again.'); setState('error')
    }
  }

  if (state === 'done') {
    return (
      <div className="pop-in inline-flex items-center gap-3 rounded-xl border border-[#14B8A6]/30 bg-[#14B8A6]/8 px-4 py-3">
        <span className="grid h-7 w-7 place-items-center rounded-full bg-[#14B8A6] text-white">
          <Check size={16} strokeWidth={3} />
        </span>
        <div className="text-left">
          <div className="text-[15px] font-semibold text-[#0F172A]">You're on the list — check your inbox!</div>
          <div className="text-[13px] text-[#64748B]">Confirmation sent to {email}</div>
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
              'h-12 w-full rounded-xl border bg-white px-4 text-[15px] text-[#0F172A] outline-none transition placeholder:text-[#94A3B8] disabled:opacity-60',
              state === 'error'
                ? 'border-red-400 ring-2 ring-red-100'
                : 'border-[#E2E8F0] focus:border-[#0EA5E9] focus:ring-2 focus:ring-[#0EA5E9]/15',
            ].join(' ')}
          />
        </div>
        <button
          type="submit"
          disabled={state === 'loading'}
          className="group inline-flex h-12 items-center justify-center gap-2 rounded-xl bg-[#0EA5E9] px-5 text-[15px] font-semibold text-white shadow-[0_8px_24px_-8px_rgba(14,165,233,0.6)] transition hover:bg-[#0284C7] active:scale-[0.98] disabled:opacity-60"
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
      <div className="mt-2 h-4 text-[13px] text-red-500">{errMsg}</div>
    </form>
  )
}
