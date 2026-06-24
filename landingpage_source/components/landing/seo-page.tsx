'use client'

import { useEffect, useState, useRef } from 'react'
import Image from 'next/image'
import {
  ShieldAlert, ClipboardCheck, FileSignature, Users, Check,
  CheckCircle2, Shield,
} from 'lucide-react'
import { WaitlistForm } from './waitlist-form'
import { HowTabs } from './how-tabs'

const BASE = process.env.NEXT_PUBLIC_ASSET_BASE ?? ''

// ── [Hook] 카운트업 ────────────────────────────────────────────────────────────
function useCountUp(end: number, duration = 1200, active = false) {
  // SSR: 최종값으로 초기화 → 정적 HTML / JS 미로딩 시에도 올바른 숫자 표시
  const [count, setCount] = useState(end)
  const hasAnimated = useRef(false)

  useEffect(() => {
    if (!active || hasAnimated.current) return
    hasAnimated.current = true
    let startTs: number | null = null
    const step = (ts: number) => {
      if (!startTs) startTs = ts
      const progress = Math.min((ts - startTs) / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setCount(Math.round(eased * end))
      if (progress < 1) window.requestAnimationFrame(step)
      else setCount(end)
    }
    window.requestAnimationFrame(step)
  }, [end, duration, active])

  return count
}

// ── [Data] ────────────────────────────────────────────────────────────────────
const goodmanCriteria = [
  'Age over 50 or under 20 years',
  'History of cancer / prior malignancy',
  'Unexplained weight loss or systemic signs',
  'Pain unrelieved by rest or position change',
  'Severe, constant, progressive nighttime pain',
  'Failure to improve after 4–6 weeks of PT',
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

const FULL_TEXT =
  'Worsening, deep, constant low back pain × 3 weeks. Unrelieved by rest. Hx prostate cancer tx 4 yrs ago.'

// ── [Page] ────────────────────────────────────────────────────────────────────
export function SeoPage() {
  // Hero typing + alarm
  const [heroText, setHeroText] = useState('')
  const [isAlertActive, setIsAlertActive] = useState(false)

  // Scroll triggers
  const [painsVisible, setPainsVisible] = useState(false)
  const [goodmanVisible, setGoodmanVisible] = useState(false)
  const painsRef = useRef<HTMLDivElement>(null)
  const goodmanRef = useRef<HTMLDivElement>(null)

  // Goodman checklist step
  const [checkedSteps, setCheckedSteps] = useState(0)

  // Counters (3 pain cards, fixed — hooks must be at top level)
  const countRevenue = useCountUp(90, 1200, painsVisible)   // $30K–$90K/yr
  const countMalp = useCountUp(134, 1200, painsVisible)     // $134K

  // Pain display values — Financial → Legal → Existential
  const pains = [
    {
      tag: 'Revenue Loss',
      stat: `$30K–$${countRevenue}K/yr`,
      title: 'Lost to Claim Denials',
      body: "PT clinics lose $30K–$90K annually to preventable denials. 'Missing information' is the #1 reason.",
      source: 'CMS Denial Rate Data / SPRY PT Industry Report',
    },
    {
      tag: 'HPSO Report',
      stat: `$${countMalp}K`,
      title: 'Average PT Malpractice Lawsuit',
      body: "Improper management of patient treatment is the #1 malpractice allegation against PTs — and your PTA's blind spot is your legal exposure.",
      source: 'HPSO Physical Therapy Professional Liability Exposure Claim Report, 4th Edition',
    },
    {
      tag: 'CMS Compliance',
      stat: 'Zero Notice',
      title: 'Before Medicare Exclusion',
      body: "A single PTA supervision violation can trigger repayment demands and full Medicare exclusion. Most clinics don't know until it's too late.",
      source: 'OIG Audit Protocol',
    },
  ]

  // Effect: Hero typing
  useEffect(() => {
    let i = 0
    let blinkTimer: ReturnType<typeof setTimeout> | null = null
    const timer = setInterval(() => {
      setHeroText(FULL_TEXT.slice(0, i + 1))
      i++
      if (i >= FULL_TEXT.length) {
        clearInterval(timer)
        blinkTimer = setTimeout(() => setIsAlertActive(true), 400)
      }
    }, 25)
    return () => {
      clearInterval(timer)
      if (blinkTimer) clearTimeout(blinkTimer)
    }
  }, [])

  // Effect: Scroll observers
  useEffect(() => {
    const opts = { threshold: 0.15, rootMargin: '0px 0px -50px 0px' }

    const painsObs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { setPainsVisible(true); painsObs.disconnect() }
    }, opts)
    const goodmanObs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { setGoodmanVisible(true); goodmanObs.disconnect() }
    }, opts)

    if (painsRef.current) painsObs.observe(painsRef.current)
    if (goodmanRef.current) goodmanObs.observe(goodmanRef.current)
    return () => { painsObs.disconnect(); goodmanObs.disconnect() }
  }, [])

  // Effect: Goodman checklist sequential reveal
  useEffect(() => {
    if (!goodmanVisible) return
    const interval = setInterval(() => {
      setCheckedSteps((prev) => {
        if (prev >= goodmanCriteria.length) { clearInterval(interval); return prev }
        return prev + 1
      })
    }, 400)
    return () => clearInterval(interval)
  }, [goodmanVisible])

  return (
    <div className="min-h-screen bg-white text-slate-900 antialiased">

      {/* ── Hero ──────────────────────────────────────────────── */}
      <header className="relative overflow-hidden pb-24 pt-8" style={{ background: 'linear-gradient(180deg,#f8fafc,#ffffff)' }}>
        <div aria-hidden className="pointer-events-none absolute inset-0"
          style={{
            backgroundImage: 'linear-gradient(rgba(15,23,42,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(15,23,42,.05) 1px,transparent 1px)',
            backgroundSize: '58px 58px',
            WebkitMaskImage: 'radial-gradient(120% 90% at 70% 0%, #000 30%, transparent 75%)',
            maskImage: 'radial-gradient(120% 90% at 70% 0%, #000 30%, transparent 75%)',
          }}
        />

        <div className="relative mx-auto flex max-w-6xl items-center justify-between px-5 pb-10 sm:px-8">
          <Image src={`${BASE}/logo-lockup.png`} alt="SagePontus" width={180} height={40} className="h-9 w-auto" priority />
          <nav className="hidden items-center gap-7 text-[14px] font-medium text-slate-500 sm:flex">
            <span className="cursor-pointer hover:text-slate-900">Product</span>
            <span className="cursor-pointer hover:text-slate-900">Safety</span>
            <span className="cursor-pointer hover:text-slate-900">Pricing</span>
            <span className="cursor-pointer hover:text-slate-900">Blog</span>
            <a href={`${process.env.NEXT_PUBLIC_PT_APP_URL ?? ''}/pt/login/`} className="inline-flex items-center rounded-lg border border-slate-300 bg-white px-4 py-1.5 text-[14px] font-semibold text-slate-700 shadow-sm hover:border-sky-400 hover:text-sky-500 transition-colors">Sign in</a>
          </nav>
        </div>

        <div className="relative mx-auto max-w-6xl px-5 sm:px-8">
          <div className="grid items-center gap-14 lg:grid-cols-2 lg:gap-10">

            {/* Left */}
            <div>
              <span className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-sky-600">
                ✦ AI PT Compliance Tool · Chrome Extension
              </span>
              <h1 className="mt-5 font-display text-[clamp(2.4rem,4.6vw,3.9rem)] font-bold leading-[1.04] tracking-[-0.025em] text-slate-900">
                Red Flag Detected.<br />
                <span className="bg-gradient-to-r from-teal-500 to-sky-500 bg-clip-text text-transparent">
                  Before Treatment Starts.
                </span>
              </h1>
              <p className="mt-6 text-lg leading-relaxed text-slate-600">
                  Enter symptoms. SagePontus screens against{' '}
                  <strong className="font-semibold text-slate-900">
                    Goodman&apos;s 6 physical therapy red flag criteria
                  </strong>{' '}
                  in real time — and alerts before your PTA takes another step.
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

            {/* Right: product mock with typing + alarm */}
            <div className="pb-10 pt-4 lg:pl-6 lg:pt-0">
              <div className="relative mx-auto w-full">
                <div className="overflow-hidden rounded-2xl bg-white shadow-[0_40px_80px_-36px_rgba(15,23,42,.28)] ring-1 ring-slate-200/80">
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
                    <div className="space-y-3.5 sm:border-r sm:border-slate-100 sm:pr-4">
                      <div>
                        <span className="block text-[10.5px] font-bold uppercase tracking-wide text-slate-400">Subjective</span>
                        <p className="mt-1.5 min-h-[64px] rounded-lg border border-slate-200/60 bg-slate-50 p-2.5 font-mono text-[12px] leading-relaxed text-slate-700">
                          {heroText}
                          {!isAlertActive && (
                            <span className="ml-0.5 inline-block h-3 w-[2px] animate-pulse bg-sky-500 align-middle" />
                          )}
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

                    <div className="flex items-center justify-center">
                      <div
                        className={`overflow-hidden rounded-xl border bg-white transition-all duration-500 ${
                          isAlertActive
                            ? 'alarm-pulse border-rose-300 shadow-[0_0_24px_rgba(244,63,94,.35)]'
                            : 'border-slate-200 opacity-40'
                        }`}
                        style={{ maxWidth: '220px' }}
                      >
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
              A missed Red Flag can end your career. A compliance gap can cost your clinic everything. SagePontus catches both — before anyone asks.
            </p>
          </div>
          {/* painsRef: scroll trigger for counters */}
          <div ref={painsRef} className="mt-12 grid gap-5 md:grid-cols-3">
            {pains.map((p, i) => (
              <div
                key={i}
                className="group relative flex h-full flex-col justify-between rounded-2xl border border-slate-100 bg-white p-8 shadow-[0_2px_8px_rgba(15,23,42,0.02)] transition-all duration-300 hover:-translate-y-0.5 hover:border-slate-200/80 hover:shadow-[0_16px_32px_-12px_rgba(15,23,42,0.1)]"
              >
                <div>
                  <div className="mb-6 inline-flex items-center rounded border border-slate-200/60 bg-slate-50 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-slate-400">
                    {p.tag}
                  </div>
                  <div className="mb-2 font-sans text-4xl font-black tracking-tight text-sky-600" aria-hidden="true">
                    {p.stat}
                  </div>
                  <h3 className="mb-3 text-lg font-bold tracking-tight text-slate-900">{p.title}</h3>
                  <p className="text-sm leading-relaxed text-slate-500">{p.body}</p>
                </div>
                <div className="mt-6 border-t border-slate-100 pt-4 text-[11px] font-medium italic text-slate-400">
                  Source: <cite>{p.source}</cite>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ──────────────────────────────────────── */}
      <section className="border-y border-slate-200 bg-slate-100 py-20 sm:py-28">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-600">How SagePontus Works</h2>
          </div>
          <div className="mt-8">
            <HowTabs />
          </div>
        </div>
      </section>

      {/* ── Goodman's 6 criteria checklist ────────────────────── */}
<section className="py-20 sm:py-28 bg-white">
  <div className="mx-auto max-w-6xl px-5 sm:px-8">
    <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-16">

      {/* Left: Copy & Authority (E-E-A-T Section) */}
      <div>
        {/* H2 아래 배치되는 명확한 문맥 서브타이틀 */}
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-600">
          The Clinical Standard Behind SagePontus
        </p>
        
        {/* H2: 핵심 롱테일 키워드가 포함된 메인 헤딩 */}
        <h2 className="mt-2.5 font-display text-[clamp(1.85rem,3.4vw,2.7rem)] font-bold leading-[1.1] tracking-[-0.02em] text-slate-900">
          Built on Goodman&apos;s<br />6 Red Flag Criteria
        </h2>
        
        {/* P: 서비스의 '실시간 리스크 차단' 포지셔닝 문맥 강화 */}
        <p className="mt-4 text-lg text-slate-600">
          Not AI guesswork — every screen runs the same evidence-based protocol physical therapists learn in school. The same criteria that, when missed, become the basis for malpractice suits.
        </p>
        
        {/* 의학 서적 정석 출처 인용으로 YMYL 신뢰도 보장 */}
        <p className="mt-3 text-sm text-slate-400">
          Source: <cite className="not-italic">Goodman C, Snyder T. <em>Differential Diagnosis for Physical Therapists</em>, 5th ed.</cite>
        </p>
      </div>

      {/* Right: Animated Checklist (Semantic SEO Structuring) */}
      <div ref={goodmanRef}>
        {/* 
          ★ 기존 div를 ol(Ordered List) 태그로 변경하여 
          검색 로봇에게 '순서가 있는 6가지 기준 데이터'임을 명학하게 선언합니다.
        */}
        <ol 
          className="space-y-3" 
          aria-label="Goodman's 6 Clinical Red Flag Criteria Checklist"
        >
          {goodmanCriteria.map((criterion, i) => (
            /* ★ 기존 div를 li(List Item) 태그로 변경하여 스니펫 수집률을 극대화합니다. */
            <li
              key={i}
              className={`flex items-center justify-between gap-3.5 rounded-xl border px-5 py-3.5 transition-all duration-500 ${
                i < checkedSteps
                  ? 'border-teal-100 bg-teal-50/60 opacity-100 translate-y-0'
                  : 'border-slate-100 bg-white opacity-40 translate-y-1'
              }`}
              style={{ transitionDelay: `${i * 40}ms` }}
            >
              <div className="flex items-center gap-3.5">
                {/* 체크 박스 아이콘 비주얼 */}
                <span
                  className={`grid h-6 w-6 shrink-0 place-items-center rounded-full border-2 transition-all duration-300 ${
                    i < checkedSteps
                      ? 'border-teal-500 bg-teal-500 text-white'
                      : 'border-slate-200 bg-white text-transparent'
                  }`}
                  aria-hidden="true" // 스크린 리더가 단순 아이콘을 중복해 읽지 않도록 방지
                >
                  <Check size={13} strokeWidth={3} />
                </span>
                
                {/* 실제 기준 텍스트 */}
                <span className={`text-[15px] font-medium transition-colors duration-300 ${
                  i < checkedSteps ? 'text-slate-800' : 'text-slate-400'
                }`}>
                  {criterion}
                </span>
              </div>

              {/* 마지막 항목에 붙는 추가 정보 태그 */}
              {i === goodmanCriteria.length - 1 && i < checkedSteps && (
                <span className="shrink-0 rounded-md border border-sky-100 bg-sky-50 px-2 py-0.5 text-[10px] font-semibold text-sky-600">
                  Tracked across sessions
                </span>
              )}
            </li>
          ))}
        </ol>
      </div>

    </div>
  </div>
</section>


      {/* ── Features ──────────────────────────────────────────── */}
      <section className="border-t border-slate-100 bg-slate-50/50 py-20 sm:py-28">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sky-600">What you get</p>
            <h2 className="mt-2.5 font-display text-[clamp(1.85rem,3.4vw,2.7rem)] font-bold leading-[1.1] tracking-[-0.02em] text-slate-900">
              Three layers of PT compliance protection. One extension.
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
<section className="py-20 sm:py-28 bg-white">
  <div className="mx-auto max-w-6xl px-6">
    
    {/* 정석 SEO와 강력한 후킹을 모두 잡은 타이틀 영역 */}
    <div className="mx-auto max-w-2xl text-center mb-12 sm:mb-16">
      <p className="text-[13px] font-semibold uppercase tracking-widest text-[#0EA5E9] mb-3">
        {proof.label} {/* WHAT PTs ARE SAYING */}
      </p>
      {/* ★ SEO 최적화: 타겟 도메인이 명확히 박힌 H2 */}
      <h2 className="font-display text-[clamp(1.85rem,3.4vw,2.7rem)] font-bold leading-[1.1] tracking-[-0.02em] text-slate-900">
        This is what physical therapists are dealing with right now.
      </h2>
      {/* ★ SEO 최적화: 서비스의 실시간 리스크 차단 포지셔닝이 녹아든 본문 */}
      <p className="mt-4 text-lg text-slate-600">
        Red flags get missed. Critical changes go unreported. Notes don't hold up in audit.
      </p>
    </div>

    {/* 리뷰 카드 그리드 (blockquote + cite 구조 유지) */}
    <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-4">
      {proof.quotes.map((q, i) => (
        <blockquote
          key={i}
          className="flex flex-col gap-4 rounded-2xl border border-[#E2E8F0] bg-white p-6 shadow-sm hover:shadow-md transition-shadow duration-200"
        >
          <p className="text-[15px] leading-relaxed text-[#475569]">❝ {q.quote} ❞</p>
          <div className="mt-auto flex items-center gap-3">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-gradient-to-br from-[#0EA5E9] to-[#14B8A6] text-[12px] font-bold text-white">
              {q.initials}
            </span>
            <cite className="not-italic text-[13px] text-[#94A3B8]">{q.attribution}</cite>
          </div>
        </blockquote>
      ))}
    </div>

    {/* 하단 마무리 카피 */}
    <p className="mt-10 text-center text-[14px] font-medium text-[#64748B] max-w-2xl mx-auto">
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
                Be first to access SagePontus when we launch.
              </h2>
              <p className="mt-3 text-lg text-slate-300">Early members get founding member pricing.</p>
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
          <Image src={`${BASE}/logo-lockup.png`} alt="SagePontus" width={90} height={20} className="h-4.5 w-auto" />
          <div className="flex flex-col items-center gap-1.5 text-center sm:items-end sm:text-right">
            <p className="text-sm text-slate-500">© 2026 SagePontus · For Physical Therapists</p>
            <address className="flex flex-col gap-1 not-italic font-sans text-xs tracking-tight text-slate-400 sm:flex-row sm:gap-3">
              <span>
                <strong className="font-semibold text-slate-500">Contact:</strong>{' '}
                <a href="mailto:contact@sagepontus.com" className="hover:text-slate-600 hover:underline">contact@sagepontus.com</a>
              </span>
              <span className="hidden text-slate-300 sm:inline">|</span>
              <span>
                <strong className="font-semibold text-slate-500">Address:</strong> Startup Venture Campus, 100 Middlefield Rd. Menlo Park, CA 94025, USA
              </span>
            </address>
          </div>
        </div>
      </footer>

    </div>
  )
}
