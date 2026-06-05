import Image from 'next/image'
import {
  ShieldAlert, ClipboardCheck, FileSignature, Users,
  Zap, ShieldCheck, CheckCircle2, Shield,
} from 'lucide-react'
import { WaitlistForm } from '@/components/landing/waitlist-form'
import { HowTabs } from '@/components/landing/how-tabs'

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="mb-3 text-[13px] font-semibold uppercase tracking-[0.14em] text-[#0EA5E9]">
      {children}
    </div>
  )
}

const pains = [
  {
    img: '/icon-gavel.png',
    stat: '$134K',
    title: 'Average PT Malpractice Lawsuit',
    body: "PT is the #1 medical field for malpractice claims. Your PTA's blind spot is your legal exposure.",
  },
  {
    img: '/icon-clock.png',
    stat: '$47K/yr',
    title: 'Lost to Documentation Overhead',
    body: 'Every hour spent on paperwork is an hour not treating — and revenue quietly walking out the door.',
  },
  {
    img: '/icon-shield-alert.png',
    stat: 'Zero Notice',
    title: 'Before Medicare Exclusion',
    body: "A single PTA supervision violation can trigger repayment demands, penalties, and full Medicare exclusion. Most clinics don't know until it's too late.",
  },
]

const features = [
  {
    icon: <ShieldAlert size={22} />,
    spark: true,
    title: 'The Malpractice Shield',
    body: "Instantly scans session notes against 50+ clinical patterns (Goodman's Guidelines) to catch hidden cancer, fractures, or vascular emergencies before liability strikes.",
    tag: 'For Clinic Directors',
  },
  {
    icon: <ClipboardCheck size={22} />,
    spark: false,
    title: 'Screening proof, not just session notes',
    body: "Every red flag screening is timestamped and stored. When a lawyer asks 'did you screen?' — you have a record, not a memory.",
    tag: 'For Clinic Directors',
  },
  {
    icon: <FileSignature size={22} />,
    spark: false,
    title: 'Audit-Proof Referral Generator',
    body: "Physician referral and medical necessity letters generated in seconds. Backed by clinical evidence that MDs respect — and keeps your clinic off the Medicare audit list.",
    tag: 'For Clinic Directors',
  },
]

const proof = {
  line: 'Trusted by early-access PTs across California, Texas, and Florida',
  people: [
    { initials: 'RM', name: 'Dr. Rivera',  role: 'DPT · Austin, TX' },
    { initials: 'JL', name: 'J. Lin',      role: 'Clinic Director · San Diego, CA' },
    { initials: 'AK', name: 'A. Kaur',     role: 'PTA · Miami, FL' },
  ],
}

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white text-[#0F172A]">

      {/* ── Nav ───────────────────────────────────────────────── */}
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 pt-8 pb-2">
        <div className="flex items-center">
          <Image src="/logo-lockup.png" alt="SagePontus" width={180} height={40} className="h-9 w-auto" priority />
        </div>
        <nav className="hidden items-center gap-7 text-[14px] font-medium text-[#475569] sm:flex">
          <span className="cursor-pointer hover:text-[#0F172A]">Product</span>
          <span className="cursor-pointer hover:text-[#0F172A]">Safety</span>
          <span className="cursor-pointer hover:text-[#0F172A]">Pricing</span>
          <span className="cursor-pointer rounded-lg border border-[#E2E8F0] px-3 py-1.5 hover:border-[#0EA5E9] hover:text-[#0EA5E9]">
            Sign in
          </span>
        </nav>
      </header>

      {/* ── Hero ──────────────────────────────────────────────── */}
      <section className="mx-auto max-w-6xl px-6 pt-16 pb-20">
        <div className="reveal inline-flex items-center gap-2 rounded-full border border-[#E2E8F0] bg-[#F8FAFC] px-3 py-1.5 text-[13px] font-medium text-[#475569]">
          <span className="h-1.5 w-1.5 rounded-full bg-[#14B8A6]" />
          Chrome extension · Private beta
        </div>

        <h1
          className="reveal mt-6 max-w-3xl text-[clamp(2.4rem,6vw,4.2rem)] font-extrabold leading-[1.02] tracking-[-0.03em]"
          style={{ animationDelay: '0.05s' }}
        >
          Your PTA Missed a Red Flag.
          <br />
          <span className="bg-gradient-to-r from-[#0EA5E9] to-[#14B8A6] bg-clip-text text-transparent">
            You Just Inherited a $134K Lawsuit.
          </span>
        </h1>

        <p
          className="reveal mt-6 max-w-2xl text-[19px] leading-relaxed text-[#475569]"
          style={{ animationDelay: '0.1s' }}
        >
          Direct Access gave PTAs more power. It also gave YOU more liability. SagePontus flags
          what humans miss — before it becomes your problem.
        </p>

        <div className="reveal mt-8 max-w-xl" style={{ animationDelay: '0.15s' }}>
          <WaitlistForm />
        </div>

        <div
          className="reveal -mt-1 flex items-center gap-2 text-[13.5px] text-[#64748B]"
          style={{ animationDelay: '0.2s' }}
        >
          <CheckCircle2 size={15} className="text-[#14B8A6]" />
          Free during beta · No credit card
        </div>

        {/* Product mockup */}
        <div
          className="reveal mt-14 overflow-hidden rounded-2xl border border-[#E2E8F0] bg-[#F8FAFC] shadow-[0_30px_80px_-40px_rgba(15,23,42,0.4)]"
          style={{ animationDelay: '0.25s' }}
        >
          <div className="flex items-center justify-center p-6">
            <Image
              src="/alarm-panel.png"
              alt="Sage Pontus Red Flag Alert panel"
              width={900}
              height={520}
              className="w-full h-auto rounded-xl drop-shadow-md"
              priority
            />
          </div>
        </div>
      </section>

      {/* ── Pain points ───────────────────────────────────────── */}
      <section className="border-y border-[#E2E8F0] bg-[#F8FAFC]">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <SectionLabel>The hidden cost</SectionLabel>
          <h2 className="max-w-2xl text-[clamp(1.8rem,3.5vw,2.6rem)] font-bold tracking-[-0.02em]">
            Every clinic loses time and carries risk they can&apos;t see.
          </h2>
          <div className="mt-10 grid gap-5 sm:grid-cols-3">
            {pains.map((p, i) => (
              <div
                key={i}
                className="rounded-2xl border border-[#E2E8F0] bg-white p-6 transition hover:-translate-y-1 hover:border-[#0EA5E9]/40 hover:shadow-[0_20px_50px_-30px_rgba(14,165,233,0.5)]"
              >
                <span className="grid h-11 w-11 place-items-center rounded-xl bg-[#0EA5E9]/10">
                  <Image src={p.img} alt={p.title} width={28} height={28} />
                </span>
                <div className="mt-5 text-[26px] font-extrabold tracking-tight text-[#0F172A]">
                  {p.stat}
                </div>
                <div className="text-[15px] font-semibold text-[#0F172A]">{p.title}</div>
                <p className="mt-2 text-[14px] leading-relaxed text-[#64748B]">{p.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── How it works ──────────────────────────────────────── */}
      <section className="mx-auto max-w-6xl px-6 py-20">
        <SectionLabel>How it works</SectionLabel>
        <HowTabs />
      </section>

      {/* ── Features bento ────────────────────────────────────── */}
      <section className="border-t border-[#E2E8F0] bg-[#F8FAFC]">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <SectionLabel>What you get</SectionLabel>
          <h2 className="max-w-2xl text-[clamp(1.8rem,3.5vw,2.6rem)] font-bold tracking-[-0.02em]">
            Three layers of protection. One extension.
          </h2>
          <div className="mt-10 grid gap-5 md:grid-cols-3">
            {features.map((f, i) => (
              <div
                key={i}
                className="group flex flex-col rounded-2xl border border-[#E2E8F0] bg-white p-7 transition hover:-translate-y-1 hover:shadow-[0_24px_60px_-36px_rgba(15,23,42,0.5)]"
              >
                <div className="relative inline-flex">
                  <span className="grid h-12 w-12 place-items-center rounded-xl bg-gradient-to-br from-[#0EA5E9] to-[#14B8A6] text-white shadow-[0_10px_24px_-10px_rgba(14,165,233,0.7)]">
                    {f.icon}
                  </span>
                  {f.spark && (
                    <span className="absolute -right-1.5 -top-1.5 grid h-5 w-5 place-items-center rounded-full bg-[#0F172A] text-[#CCFF00]">
                      <Zap size={11} />
                    </span>
                  )}
                </div>
                <h3 className="mt-5 text-[19px] font-bold tracking-tight">{f.title}</h3>
                <p className="mt-2 flex-1 text-[14.5px] leading-relaxed text-[#64748B]">{f.body}</p>
                <span className="mt-5 inline-flex w-fit items-center gap-1.5 rounded-full border border-[#E2E8F0] bg-[#F8FAFC] px-3 py-1 text-[12.5px] font-semibold text-[#475569]">
                  <Users size={12} /> {f.tag}
                </span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Social proof ──────────────────────────────────────── */}
      <section className="mx-auto max-w-6xl px-6 py-16">
        <div className="flex flex-col items-center gap-6 rounded-2xl border border-[#E2E8F0] bg-white p-8 text-center">
          <div className="flex -space-x-3">
            {proof.people.map((p, i) => (
              <span
                key={i}
                className="grid h-11 w-11 place-items-center rounded-full border-2 border-white bg-gradient-to-br from-[#0EA5E9] to-[#14B8A6] text-[13px] font-bold text-white shadow"
              >
                {p.initials}
              </span>
            ))}
          </div>
          <p className="text-[15px] font-medium text-[#475569]">{proof.line}</p>
        </div>
      </section>

      {/* ── Final CTA ─────────────────────────────────────────── */}
      <section className="mx-auto max-w-6xl px-6 pb-24">
        <div className="overflow-hidden rounded-3xl bg-[#0F172A] px-8 py-16 text-center sm:px-16">
          <h2 className="mx-auto max-w-xl text-[clamp(2rem,4vw,3rem)] font-extrabold tracking-[-0.02em] text-white">
            Be first when we launch.
          </h2>
          <p className="mx-auto mt-4 max-w-md text-[17px] text-[#94A3B8]">
            Beta access is limited. Early members get 6 months free.
          </p>
          <div className="mx-auto mt-8 max-w-md text-left">
            <WaitlistForm />
          </div>
        </div>
        <div className="mt-10 flex flex-col items-center justify-between gap-3 text-[13.5px] text-[#94A3B8] sm:flex-row">
          <span>© 2026 SagePontus · For Physical Therapists</span>
          <span className="flex items-center gap-2">
            <Image src="/logo-mark.png" alt="" width={16} height={16} className="opacity-60" />
            Made for clinicians, by clinicians.
          </span>
        </div>
      </section>

    </div>
  )
}
