import type { Metadata } from 'next'
import Image from 'next/image'

export const metadata: Metadata = {
  title: 'SagePontus | PT Red Flag Screening & Compliance Shield',
  description: "Protect your physical therapy clinic from malpractice lawsuits and claim denials. SagePontus screens Goodman's 6 criteria in real time.",
}
import {
  ShieldAlert, ClipboardCheck, FileSignature, Users, Check,
  CheckCircle2, Shield,
} from 'lucide-react'
import { WaitlistForm } from '@/components/landing/waitlist-form'
import { HowTabs } from '@/components/landing/how-tabs'
import { PageTabs } from '@/components/landing/page-tabs'

const BASE = process.env.NEXT_PUBLIC_ASSET_BASE ?? ''

const pains = [
  {
    tag: 'HPSO Report',
    stat: '$134K',
    title: 'Average PT Malpractice Lawsuit',
    body: "PT is the #1 medical field for malpractice claims. Your PTA's blind spot is your legal exposure.",
    source: "Source: HPSO Physical Therapy Malpractice Report, 4th Edition",
  },
  {
    tag: 'Revenue Loss',
    stat: '$30K–$90K/yr',
    title: 'Lost to Claim Denials',
    body: 'PT clinics lose $30K–$90K annually to preventable denials. "Missing information" is the #1 reason.',
    source: "Source: WebPT / APTA Benchmark Data",
  },
  {
    tag: 'CMS Compliance',
    stat: 'Zero Notice',
    title: 'Before Medicare Exclusion',
    body: "A single PTA supervision violation can trigger repayment demands and full Medicare exclusion. Most clinics don't know until it's too late.",
    source: "Regulatory Risk Factor: OIG Audit Protocol",
  },
]

const features = [
  {
    icon: <ShieldAlert size={26} />,
    title: 'The Malpractice Shield',
    body: 'Every session gets screened. SagePontus catches the hidden cancer, fracture, or vascular emergency before it becomes a $134K lawsuit.',
    tag: 'For Clinic Directors',
    points: [
      "Goodman's 6-criteria screen in real time",
      'Referral letter auto-generated on trigger',
      'Documented chain of custody — timestamped',
    ],
  },
  {
    icon: <FileSignature size={26} />,
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
    icon: <ClipboardCheck size={26} />,
    title: 'Liability Score, not gut feeling',
    body: 'SagePontus gives you a compliance number before anyone asks. Updated after every session, across every patient.',
    tag: 'For Clinic Directors',
    points: [
      'Live score updated after every session',
      'Aggregated across every PTA in your clinic',
      'Flags compliance deadlines before they expire',
    ],
  },
]

const proof = {
  label: 'WHAT PTs ARE SAYING',
  quotes: [
    {
      initials: 'PT',
      quote: 'Sent 3 patients to the ER this week — DVT, 220+ seated BP, and chest pain down the left arm. Things like this show up in outpatient settings more than people expect.',
      attribution: 'Outpatient PT · r/physicaltherapy',
    },
    {
      initials: 'PT',
      quote: 'A thorough examination and history is probably the most important thing we do. Unfortunately it takes time, and that is what seems to be constantly being taken away.',
      attribution: 'Outpatient PT · r/physicaltherapy',
    },
    {
      initials: 'DPT',
      quote: "I'd rather get over-communicated to than find out three sessions later that something important was missed.",
      attribution: 'DPT · r/physicaltherapy',
    },
    {
      initials: 'RM',
      quote: 'Notes signed days or weeks after the fact will never hold up in an audit. From a legal standpoint, most entities require documentation within 24-48 hours.',
      attribution: 'Director of Risk Management, 41 years · r/physicaltherapy',
    },
  ],
  closing: "SagePontus timestamps every screening, every session — automatically. Because \"I don't remember\" is not a legal defense.",
}

export default function LandingPage() {
  return (
    <PageTabs>
    <div className="min-h-screen bg-white text-slate-900 antialiased">

      {/* ── Hero ──────────────────────────────────────────────── */}
      <header className="relative overflow-hidden pb-24 pt-8" style={{ background: 'linear-gradient(180deg,#f8fafc,#ffffff)' }}>
        {/* Grid dot background */}
        <div aria-hidden className="pointer-events-none absolute inset-0"
          style={{
            backgroundImage: 'linear-gradient(rgba(15,23,42,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(15,23,42,.05) 1px,transparent 1px)',
            backgroundSize: '58px 58px',
            WebkitMaskImage: 'radial-gradient(120% 90% at 70% 0%, #000 30%, transparent 75%)',
            maskImage: 'radial-gradient(120% 90% at 70% 0%, #000 30%, transparent 75%)',
          }}
        />

        {/* Nav */}
        <div className="relative mx-auto flex max-w-6xl items-center justify-between px-5 pb-10 sm:px-8">
          <Image src={`${BASE}/logo-lockup.png`} alt="SagePontus" width={180} height={40} className="h-9 w-auto" priority />
          <nav className="hidden items-center gap-7 text-[14px] font-medium text-slate-500 sm:flex">
            <span className="cursor-pointer hover:text-slate-900">Product</span>
            <span className="cursor-pointer hover:text-slate-900">Safety</span>
            <span className="cursor-pointer hover:text-slate-900">Pricing</span>
            <span className="cursor-pointer hover:text-slate-900">Blog</span>
            <span className="cursor-pointer rounded-lg border border-slate-200 px-3 py-1.5 hover:border-sky-400 hover:text-sky-500">
              Sign in
            </span>
          </nav>
        </div>

        {/* Hero grid */}
        <div className="relative mx-auto max-w-6xl px-5 sm:px-8">
          <div className="grid items-center gap-14 lg:grid-cols-2 lg:gap-10">

            {/* Left: headline + form */}
            <div>
              <span className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-sky-600">
                ✦ Chrome extension · Private beta
              </span>
              <h1 className="mt-5 font-display text-[clamp(2.4rem,4.6vw,3.9rem)] font-bold leading-[1.04] tracking-[-0.025em] text-slate-900">
                Red Flag Detected.<br />
                <span className="bg-gradient-to-r from-teal-500 to-sky-500 bg-clip-text text-transparent">
                  Before Treatment Starts.
                </span>
              </h1>
              <p className="mt-6 text-lg leading-relaxed text-slate-600">
                Enter symptoms. SagePontus screens against Goodman's 6 criteria in real time — and alerts before your PTA takes the first step.
              </p>
              <div className="mt-8 max-w-md">
                <WaitlistForm />
              </div>
              <div className="mt-5 flex w-fit flex-wrap items-center gap-x-5 gap-y-2 rounded-full border border-slate-100 bg-white/75 px-4 py-2 shadow-sm backdrop-blur-sm">
                <span className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600">
                  <CheckCircle2 size={14} className="text-teal-500" /> Free during beta
                </span>
                <span className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600">
                  <CheckCircle2 size={14} className="text-teal-500" /> No credit card
                </span>
              </div>
            </div>

            {/* Right: product mock */}
            <div className="pb-10 pt-4 lg:pl-6 lg:pt-0">
              <div className="relative mx-auto w-full">
                <div className="overflow-hidden rounded-2xl bg-white shadow-[0_40px_80px_-36px_rgba(15,23,42,.28)] ring-1 ring-slate-200/80">
                  {/* Browser chrome */}
                  <div className="flex h-11 items-center gap-2 border-b border-slate-200 bg-slate-50 px-4">
                    <span className="flex gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-full bg-slate-200" />
                      <span className="h-2.5 w-2.5 rounded-full bg-slate-200" />
                      <span className="h-2.5 w-2.5 rounded-full bg-slate-200" />
                    </span>
                    <span className="ml-2 font-mono text-[10.5px] uppercase tracking-wider text-slate-400">EMR · Daily Note</span>
                    <span className="ml-auto inline-flex items-center gap-1 rounded-full border border-sky-100 bg-sky-50 px-2.5 py-0.5 text-[10.5px] font-bold text-sky-700">
                      <Shield size={11} /> SagePontus Active
                    </span>
                  </div>

                  <div className="grid gap-4 bg-white p-4 sm:grid-cols-[1fr_auto] sm:p-5">
                    {/* SOAP note */}
                    <div className="space-y-3.5 sm:border-r sm:border-slate-100 sm:pr-4">
                      <div>
                        <span className="block text-[10.5px] font-bold uppercase tracking-wide text-slate-400">Subjective</span>
                        <p className="mt-1.5 rounded-lg border border-slate-200/60 bg-slate-50 p-2.5 text-[12px] leading-relaxed text-slate-700">
                          Worsening, deep, constant low back pain × 3 weeks. Unrelieved by rest. Hx prostate cancer tx 4 yrs ago.
                        </p>
                      </div>
                      <div>
                        <span className="block text-[10.5px] font-bold uppercase tracking-wide text-slate-400">Objective</span>
                        <div className="mt-1.5 space-y-1.5">
                          <div className="flex items-center justify-between border-b border-slate-100 pb-1 text-[12px]">
                            <span className="text-slate-500">Lumbar Flexion</span>
                            <span className="font-medium text-slate-800">45° · pain-limited</span>
                          </div>
                          <div className="flex items-center justify-between text-[12px]">
                            <span className="text-slate-500">Neuro Screen</span>
                            <span className="font-medium text-slate-800">WNL · L2–S1</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Alarm panel */}
                    <div className="flex items-center justify-center">
                      <div className="alarm-pulse overflow-hidden rounded-xl border border-rose-200 bg-white" style={{ maxWidth: '220px' }}>
                        <Image
                          src={`${BASE}/alarm-panel.png`}
                          alt="SagePontus red alert — Spinal Malignancy, risk score 100%"
                          width={355}
                          height={340}
                          className="block h-auto w-full"
                          priority
                        />
                      </div>
                    </div>
                  </div>
                </div>
                <div className="absolute -bottom-4 right-5 rounded-md bg-slate-900 px-3 py-1 font-mono text-[10.5px] tracking-tight text-white shadow-md">
                  Goodman red-flag verification
                </div>
              </div>
            </div>

          </div>
        </div>
      </header>

      {/* ── Pain points ───────────────────────────────────────── */}
      <section className="py-20 sm:py-28">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-600">The hidden cost</p>
            <h2 className="mt-2.5 max-w-3xl font-display text-[clamp(1.85rem,3.4vw,2.7rem)] font-bold leading-[1.1] tracking-[-0.02em] text-slate-900">
              Every clinic loses time and carries risk they can&apos;t see.
            </h2>
            <p className="mt-4 max-w-2xl text-lg text-slate-600">
              Documentation eats your day — and a missed Red Flag can end your career. Sagepontus takes on both.
            </p>
          </div>
          <div className="mt-12 grid gap-5 md:grid-cols-3">
            {pains.map((p, i) => (
              <div
                key={i}
                className="group relative flex h-full flex-col justify-between rounded-2xl border border-slate-100 bg-white p-8 shadow-[0_2px_8px_rgba(15,23,42,0.02)] transition-all duration-300 hover:-translate-y-0.5 hover:border-slate-200/80 hover:shadow-[0_16px_32px_-12px_rgba(15,23,42,0.1)]"
              >
                <div>
                  <div className="mb-6 inline-flex items-center rounded border border-slate-200/60 bg-slate-50 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-slate-400">
                    {p.tag}
                  </div>
                  <div className="mb-2 font-sans text-4xl font-black tracking-tight text-sky-500" aria-hidden="true">{p.stat}</div>
                  <h3 className="mb-3 text-lg font-bold tracking-tight text-slate-900">{p.title}</h3>
                  <p className="text-sm leading-relaxed text-slate-500">{p.body}</p>
                </div>
                {p.source && (
                  <div className="mt-6 border-t border-slate-100 pt-4 text-[11px] font-medium italic text-slate-400">
                    <cite>{p.source}</cite>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ──────────────────────────────────────── */}
      <section className="border-y border-slate-200 bg-slate-100 py-20 sm:py-28">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-600">How it works</p>
          </div>
          <div className="mt-8">
            <HowTabs />
          </div>
        </div>
      </section>

      {/* ── Features ──────────────────────────────────────────── */}
      <section className="py-20 sm:py-28">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-600">What you get</p>
            <h2 className="mt-2.5 font-display text-[clamp(1.85rem,3.4vw,2.7rem)] font-bold leading-[1.1] tracking-[-0.02em] text-slate-900">
              Three layers of protection. One extension.
            </h2>
          </div>
          <div className="mt-12 grid gap-6 md:grid-cols-3">
            {features.map((f, i) => (
              <div
                key={i}
                className="relative h-full rounded-2xl border border-slate-200 bg-white p-7 transition duration-200 hover:border-teal-300 hover:shadow-[0_20px_50px_-28px_rgba(15,23,42,.3)]"
              >
                <div className="flex items-center justify-between gap-4">
                  <div className="grid h-14 w-14 place-items-center rounded-xl border border-teal-200 bg-teal-50 text-teal-600">
                    {f.icon}
                  </div>
                  <span className="inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-600">
                    <Users size={11} /> {f.tag}
                  </span>
                </div>
                <h3 className="mt-5 font-display text-2xl font-bold tracking-tight text-slate-900">{f.title}</h3>
                <p className="mt-3 text-[15px] leading-relaxed text-slate-600">{f.body}</p>
                <ul className="mt-6 space-y-3">
                  {f.points.map((pt, j) => (
                    <li key={j} className="flex items-start gap-2.5 text-[15px] text-slate-700">
                      <span className="mt-0.5 grid h-5 w-5 shrink-0 place-items-center rounded-md border border-teal-100 bg-teal-50 text-teal-600">
                        <Check size={12} />
                      </span>
                      {pt}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

 {/* ── Social proof ──────────────────────────────────────── */}
{/* 1. 배경색(bg-slate-50)을 전체 너비로 깔아줍니다 */}
<section className="bg-slate-50 py-16">
  {/* 2. 기존의 중앙 정렬 및 최대 너비 설정을 내부 컨테이너로 이동합니다 */}
  <div className="mx-auto max-w-6xl px-6">
    
    <p className="text-center text-[13px] font-semibold uppercase tracking-widest text-[#0EA5E9] mb-10">
      {proof.label}
    </p>

    <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
      {proof.quotes.map((q, i) => (
        <div
          key={i}
          className="flex flex-col gap-4 rounded-2xl border border-[#E2E8F0] bg-white p-6 shadow-sm"
        >
          <p className="text-[15px] text-[#475569] leading-relaxed">
            ❝ {q.quote} ❞
          </p>
          <div className="flex items-center gap-3 mt-auto">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-gradient-to-br from-[#0EA5E9] to-[#14B8A6] text-[12px] font-bold text-white">
              {q.initials}
            </span>
            <span className="text-[13px] text-[#94A3B8]">{q.attribution}</span>
          </div>
        </div>
      ))}
    </div>

    <p className="mt-8 text-center text-[14px] text-[#64748B] font-medium">
      {proof.closing}
    </p>
    
  </div>
</section>

      {/* ── Final CTA ─────────────────────────────────────────── */}
      <section className="bg-sky-950 py-20 sm:py-28">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <div className="grid items-center gap-10 lg:grid-cols-2">
            <div>
              <h2 className="font-display text-[clamp(1.9rem,4vw,3rem)] font-bold leading-tight tracking-[-0.02em] text-white">
                Be first when we launch.
              </h2>
              <p className="mt-3 text-lg text-slate-300">Beta access is limited. Early members get 6 months free.</p>
            </div>
            <div className="flex flex-col gap-3 lg:items-end">
              <WaitlistForm dark />
              <p className="text-sm text-slate-400">No credit card · Cancel anytime</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Footer ────────────────────────────────────────────── */}
     <footer className="border-t border-slate-200">
  <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-5 py-9 sm:flex-row sm:px-8">
    {/* 좌측: 로고 */}
    <Image 
      src={`${BASE}/logo-lockup.png`} 
      alt="SagePontus" 
      width={90} 
      height={20} 
      className="h-4.5 w-auto" 
      priority 
    />
    
    {/* 우측: 카피라이트 및 회사 정보 (세로 정렬 및 모바일 중앙/데스크톱 우측 정렬) */}
    <div className="flex flex-col items-center gap-1.5 text-center sm:items-end sm:text-right">
      <p className="text-sm text-slate-500">
        © 2026 SagePontus · For Physical Therapists
      </p>
      
      <address className="flex flex-col gap-1 not-italic font-sans text-xs tracking-tight text-slate-400 sm:flex-row sm:gap-3">
        {/* 방금 만든 Contact 이메일 추가 */}
        <span>
          <strong className="font-semibold text-slate-500">Contact:</strong>{' '}
          <a href="mailto:contact@sagepontus.com" className="hover:text-slate-600 hover:underline">
            contact@sagepontus.com
          </a>
        </span>
        {/* 데스크톱 화면에서 이메일과 주소 사이 구분선 (모바일에선 숨김) */}
        <span className="hidden text-slate-300 sm:inline">|</span>
        <span>
          <strong className="font-semibold text-slate-500">Address:</strong> Startup Venture Campus, 100 Middlefield Rd. Menlo Park, CA 94025, USA
        </span>
      </address>
    </div>
  </div>
</footer>

    </div>
    </PageTabs>
  )
}
