'use client'

import { useState, useEffect } from 'react'
import Image from 'next/image'
import {
  ArrowRight, ShieldAlert, FileSignature, ClipboardCheck,
  CheckCircle2, ShieldCheck, Users, Clock,
} from 'lucide-react'
import { WaitlistForm } from './waitlist-form'
import { HowTabs } from './how-tabs'

const BASE = process.env.NEXT_PUBLIC_ASSET_BASE ?? ''

// ── scroll to final CTA + focus input ────────────────────────────────────────
function scrollToCTA() {
  const el = document.getElementById('final-cta-authority')
  if (!el) return
  const y = el.getBoundingClientRect().top + window.scrollY - 16
  window.scrollTo({ top: y, behavior: 'smooth' })
  setTimeout(() => {
    const input = el.querySelector('input')
    if (input) input.focus({ preventScroll: true })
  }, 700)
}

// ── Sticky top bar — slides in after hero ────────────────────────────────────
function StickyTopBar() {
  const [show, setShow] = useState(false)

  useEffect(() => {
    const onScroll = () => setShow(window.scrollY > window.innerHeight * 0.6)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
    }
  }, [])

  return (
    <div
      className={`fixed top-0 inset-x-0 z-40 transition-transform duration-300 ${
        show ? 'translate-y-0' : '-translate-y-full'
      }`}
    >
      <div className="bg-white/90 backdrop-blur-md border-b border-slate-200">
        <div className="mx-auto max-w-6xl px-5 sm:px-8 h-14 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2.5">
            <Image
              src={`${BASE}/logo-lockup.png`}
              alt="SagePontus"
              width={140}
              height={32}
              className="h-7 w-auto"
            />
          </div>
          <button
            onClick={scrollToCTA}
            className="h-10 px-4 rounded-lg inline-flex items-center gap-1.5 font-semibold text-sm bg-sky-600 text-white hover:bg-sky-700 transition active:scale-[.98]"
          >
            Reserve access
            <ArrowRight size={15} strokeWidth={2.4} />
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Product mock (SOAP note + floating alert) ─────────────────────────────────
function ProductMock() {
  return (
    <div className="relative w-full max-w-md mx-auto">
      <div className="rounded-2xl overflow-hidden bg-white ring-1 ring-slate-200/80 shadow-[0_40px_80px_-36px_rgba(15,23,42,.28)]">
        {/* browser chrome */}
        <div className="flex items-center gap-2 px-4 h-11 border-b border-slate-100 text-slate-500">
          <span className="flex gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-300/80" />
            <span className="w-2.5 h-2.5 rounded-full bg-amber-300/80" />
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-300/80" />
          </span>
          <span className="ml-2 text-xs font-medium">WebPT · Daily Note</span>
          <span className="ml-auto inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-bold bg-sky-50 text-sky-700 ring-1 ring-sky-100">
            <ShieldCheck size={10} /> Sagepontus
          </span>
        </div>
        {/* content */}
        <div className="p-5">
          <div className="text-xs font-semibold text-sky-600">SOAP · drafted in 10s</div>
          <div className="mt-4 space-y-3.5">
            {[['S', '82%'], ['O', '94%'], ['A', '68%'], ['P', '88%']].map(([k, w]) => (
              <div key={k} className="flex items-start gap-3">
                <span className="text-[11px] font-bold text-slate-400 w-3 pt-0.5">{k}</span>
                <span className="flex-1 space-y-1.5">
                  <span className="block h-2 rounded bg-slate-200" style={{ width: w }} />
                  <span className="block h-2 rounded bg-slate-100 w-full" />
                </span>
              </div>
            ))}
          </div>
          <div className="mt-5 flex items-center justify-between rounded-xl px-3.5 py-2.5 bg-slate-50">
            <span className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-700">
              ✦ Ready to review &amp; sign
            </span>
            <span className="text-xs font-bold text-sky-600">10s</span>
          </div>
        </div>
      </div>

      {/* floating red-flag alert */}
      <div className="absolute -bottom-6 -left-3 sm:-left-8 w-[220px] rounded-xl bg-white ring-1 ring-rose-100 shadow-[0_20px_45px_-18px_rgba(244,63,94,.4)] p-3.5">
        <div className="flex items-center gap-2">
          <span className="w-7 h-7 rounded-lg bg-rose-50 text-rose-500 grid place-items-center">
            <ShieldAlert size={15} />
          </span>
          <span className="text-[11px] font-bold uppercase tracking-wide text-rose-500">Red Flag</span>
        </div>
        <p className="mt-2 text-[13px] font-semibold leading-snug text-slate-900">
          Possible vascular pattern detected
        </p>
        <button className="mt-2.5 w-full rounded-lg bg-slate-900 text-white text-[12px] font-semibold py-2 inline-flex items-center justify-center gap-1.5 hover:bg-slate-800 transition">
          Referral letter ready <ArrowRight size={13} strokeWidth={2.4} />
        </button>
      </div>
    </div>
  )
}

// ── Data ──────────────────────────────────────────────────────────────────────
const pains = [
  {
    icon: ShieldAlert,
    stat: '$134K',
    title: 'Average PT Malpractice Lawsuit',
    body: "PT is the #1 medical field for malpractice claims. Your PTA's blind spot is your legal exposure.",
    source: 'Source: HPSO Physical Therapy Malpractice Report, 4th Edition',
  },
  {
    icon: Clock,
    stat: '$30K–$90K/yr',
    title: 'Lost to Claim Denials',
    body: 'PT clinics lose $30K–$90K annually to preventable denials. "Missing information" is the #1 reason.',
    source: 'Source: SPRY PT Revenue Analysis · WebPT / APTA',
  },
  {
    icon: ClipboardCheck,
    stat: 'Zero Notice',
    title: 'Before Medicare Exclusion',
    body: 'A single PTA supervision violation can trigger repayment demands and full Medicare exclusion. Most clinics don\'t know until it\'s too late.',
  },
]

const features = [
  {
    icon: ShieldAlert,
    title: 'The Malpractice Shield',
    body: "Every session gets screened. SagePontus catches the hidden cancer, fracture, or vascular emergency before it becomes a $134K lawsuit.",
    tag: 'For Clinic Directors',
    points: [
      "Goodman's 6-criteria screen in real time",
      'Referral letter auto-generated on trigger',
      'Documented chain of custody — timestamped',
    ],
  },
  {
    icon: FileSignature,
    title: 'Audit-Proof Documentation',
    body: 'When a lawyer asks "did you screen?" — you have a record, not a memory. When an insurer says "missing information" — you have documentation that holds up.',
    tag: 'For Clinic Directors',
    points: [
      'Every session timestamped and linked to criteria',
      'Flags cite Goodman guideline chapter + page',
      'Exportable PDF trail for legal or audit review',
    ],
  },
  {
    icon: ClipboardCheck,
    title: 'Liability Score, not gut feeling',
    body: "SagePontus gives you a compliance number before anyone asks. Updated after every session, across every patient.",
    tag: 'For Clinic Directors',
    points: [
      'Live score updated after every session',
      'Aggregated across every PTA in your clinic',
      'Flags compliance deadlines before they expire',
    ],
  },
]

const quotes = [
  {
    quote: "First tool I've seen that actually addresses the supervision gap. This is what PT needs.",
    name: 'Dr. Rivera',
    role: 'DPT · Austin, TX',
    initials: 'RM',
  },
  {
    quote: "We had a near-miss last year. Sagepontus would have caught it in session 2.",
    name: 'J. Lin',
    role: 'Clinic Director · San Diego, CA',
    initials: 'JL',
  },
  {
    quote: "Charting in 10 seconds isn't a gimmick. I tested it on my hardest note of the week.",
    name: 'A. Kaur',
    role: 'PTA · Miami, FL',
    initials: 'AK',
  },
]

// ── Authority Page ────────────────────────────────────────────────────────────
export function AuthorityPage() {
  return (
    <div className="font-inter bg-white text-slate-900 antialiased">
      <StickyTopBar />

      {/* ── Hero — split layout, grid bg ─────────────────────── */}
      <header
        className="relative overflow-hidden pt-32 pb-24"
        style={{ background: 'linear-gradient(180deg,#f8fafc,#ffffff)' }}
      >
        {/* grid pattern */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0"
          style={{
            backgroundImage:
              'linear-gradient(rgba(15,23,42,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(15,23,42,.05) 1px,transparent 1px)',
            backgroundSize: '58px 58px',
            maskImage:
              'radial-gradient(120% 90% at 70% 0%, #000 30%, transparent 75%)',
            WebkitMaskImage:
              'radial-gradient(120% 90% at 70% 0%, #000 30%, transparent 75%)',
          }}
        />

        <div className="mx-auto max-w-6xl px-5 sm:px-8 relative">
          <div className="grid lg:grid-cols-2 gap-14 lg:gap-10 items-center">

            {/* left — copy + form */}
            <div>
              <span className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-sky-700">
                ✦ Chrome extension · Private beta
              </span>

              <h1 className="mt-5 font-display font-bold tracking-[-0.025em] text-slate-900 text-[clamp(2.4rem,4.6vw,3.9rem)] leading-[1.04]">
                Red Flag Detected.
                <br />
                <span className="text-sky-600">Before Treatment Starts.</span>
              </h1>

              <p className="mt-6 text-lg leading-relaxed text-slate-600">
                Enter symptoms. SagePontus screens against Goodman&apos;s 6 criteria in
                real time — and alerts before your PTA takes the first step.
              </p>

              <div className="mt-8">
                <WaitlistForm source="authority-hero" />
              </div>

              <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-2">
                {['Free during beta', 'No credit card'].map((t) => (
                  <span key={t} className="inline-flex items-center gap-1.5 text-sm text-slate-500">
                    <CheckCircle2 size={14} className="text-teal-500" /> {t}
                  </span>
                ))}
              </div>
            </div>

            {/* right — product mock */}
            <div className="lg:pl-6">
              <div className="pb-10 pt-4 lg:pt-0">
                <ProductMock />
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* ── Pain points ───────────────────────────────────────── */}
      <section className="py-20 sm:py-28">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-700">
            The hidden cost
          </p>
          <h2 className="mt-2.5 font-display font-bold tracking-[-0.02em] text-slate-900 text-[clamp(1.85rem,3.4vw,2.7rem)] leading-[1.1] max-w-3xl">
            Every clinic loses time and carries risk they can&apos;t see.
          </h2>
          <p className="mt-4 text-lg text-slate-600 max-w-2xl">
            Documentation eats your day — and a missed Red Flag can end your career.
            Sagepontus takes on both.
          </p>

          <div className="mt-12 grid gap-5 md:grid-cols-3">
            {pains.map((p, i) => {
              const Icon = p.icon
              return (
                <div
                  key={i}
                  className="group h-full rounded-xl border border-slate-200 bg-white p-7 transition duration-200 hover:border-sky-300 hover:shadow-[0_10px_30px_-18px_rgba(15,23,42,.25)]"
                >
                  <div className="w-11 h-11 rounded-lg border border-slate-200 bg-slate-50 text-sky-600 grid place-items-center transition group-hover:border-sky-200 group-hover:bg-sky-50">
                    <Icon size={20} />
                  </div>
                  <div className="mt-5 font-display text-3xl font-bold tracking-tight text-slate-900">
                    {p.stat}
                  </div>
                  <div className="mt-0.5 font-semibold text-slate-800">{p.title}</div>
                  <p className="mt-2 text-[15px] leading-relaxed text-slate-600">{p.body}</p>
                  {p.source && (
                    <p className="mt-3 text-[11.5px] text-slate-400">{p.source}</p>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      </section>

      {/* ── How it works ──────────────────────────────────────── */}
      <section className="py-20 sm:py-28 bg-slate-50/70 border-y border-slate-200/80">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <p className="text-center text-xs font-semibold uppercase tracking-[0.18em] text-sky-700 mb-1">
            How it works
          </p>
          <HowTabs />
        </div>
      </section>

      {/* ── Feature highlights ────────────────────────────────── */}
      <section className="py-20 sm:py-28">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <div className="text-center mx-auto max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-700">
              What you get
            </p>
            <h2 className="mt-2.5 font-display font-bold tracking-[-0.02em] text-slate-900 text-[clamp(1.85rem,3.4vw,2.7rem)] leading-[1.1]">
              Three layers of protection. One extension.
            </h2>
          </div>

          <div className="mt-12 grid gap-6 md:grid-cols-3">
            {features.map((f, i) => {
              const Icon = f.icon
              return (
                <div
                  key={i}
                  className="relative h-full rounded-2xl border border-slate-200 bg-white p-7 transition duration-200 hover:border-sky-300 hover:shadow-[0_20px_50px_-28px_rgba(15,23,42,.3)]"
                >
                  <div className="flex items-center justify-between gap-4">
                    <div className="w-14 h-14 rounded-xl border border-sky-200 bg-sky-50 text-sky-600 grid place-items-center">
                      <Icon size={26} />
                    </div>
                    <span className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-600">
                      <Users size={11} /> {f.tag}
                    </span>
                  </div>
                  <h3 className="mt-5 font-display font-bold text-2xl tracking-tight text-slate-900">
                    {f.title}
                  </h3>
                  <p className="mt-3 text-[15px] leading-relaxed text-slate-600">{f.body}</p>
                  <ul className="mt-6 space-y-3">
                    {f.points.map((pt) => (
                      <li key={pt} className="flex items-start gap-2.5 text-[15px] text-slate-700">
                        <span className="mt-0.5 shrink-0 w-5 h-5 rounded-md bg-sky-50 text-sky-600 grid place-items-center border border-sky-100">
                          <CheckCircle2 size={12} />
                        </span>
                        {pt}
                      </li>
                    ))}
                  </ul>
                </div>
              )
            })}
          </div>
        </div>
      </section>

      {/* ── Social proof ──────────────────────────────────────── */}
      <section className="py-20 sm:py-28 bg-slate-50/70 border-y border-slate-200/80">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <p className="text-center text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
            Trusted by early-access PTs across California, Texas, and Florida
          </p>
          <div className="mt-10 grid gap-5 md:grid-cols-3">
            {quotes.map((q, i) => (
              <figure key={i} className="h-full rounded-xl border border-slate-200 bg-white p-7">
                <blockquote className="text-[15px] leading-relaxed text-slate-700">
                  &ldquo;{q.quote}&rdquo;
                </blockquote>
                <figcaption className="mt-5 flex items-center gap-3">
                  <span className="w-9 h-9 rounded-full grid place-items-center text-xs font-bold bg-sky-100 text-sky-700 shrink-0">
                    {q.initials}
                  </span>
                  <span>
                    <span className="block font-semibold text-slate-900 text-sm">{q.name}</span>
                    <span className="block text-xs text-slate-500">{q.role}</span>
                  </span>
                </figcaption>
              </figure>
            ))}
          </div>
        </div>
      </section>

      {/* ── Final CTA — split, dark ────────────────────────────── */}
      <section id="final-cta-authority" className="py-20 sm:py-28 bg-slate-900">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <div className="grid lg:grid-cols-2 gap-10 items-center">
            <div>
              <h2 className="font-display font-bold tracking-[-0.02em] text-[clamp(1.9rem,4vw,3rem)] leading-tight text-white">
                Be first when we launch.
              </h2>
              <p className="mt-3 text-lg text-slate-300">
                Beta access is limited. Early members get 6 months free.
              </p>
            </div>
            <div className="flex flex-col gap-3 lg:items-end">
              <WaitlistForm source="authority-bottom" />
              <p className="text-sm text-slate-400">No credit card · Cancel anytime</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────── */}
      <footer className="border-t border-slate-200">
        <div className="mx-auto max-w-6xl px-5 sm:px-8 py-9 flex flex-col sm:flex-row items-center justify-between gap-4">
          <Image
            src={`${BASE}/logo-lockup.png`}
            alt="SagePontus"
            width={120}
            height={26}
            className="h-[26px] w-auto"
          />
          <p className="text-sm text-slate-500">© 2026 SagePontus · For Physical Therapists</p>
        </div>
      </footer>
    </div>
  )
}
