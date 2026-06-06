'use client'

import { useState } from 'react'

const tabs = [
  {
    id: 'ptas',
    label: 'For PTAs',
    steps: [
      {
        k: 'No new workflow required',
        v: 'Paste a session note, upload a file, or type directly — SagePontus works with however your clinic already documents.',
      },
      {
        k: 'SagePontus screens in real time',
        v: "Every symptom is automatically cross-checked against Goodman's 6 red flag criteria.",
      },
      {
        k: 'Flagged or cleared — instantly',
        v: "If a red flag fires, a physician referral letter is ready before the patient leaves the room. If not, the session is documented and closed.",
      },
    ],
  },
  {
    id: 'directors',
    label: 'For Clinic Directors',
    steps: [
      {
        k: 'Every session, automatically screened',
        v: "SagePontus runs Goodman's 6 criteria on every PTA session — with a timestamped record that screening happened.",
      },
      {
        k: 'From red flag to legal-ready documentation',
        v: 'Physician referral, medical necessity, insurance appeal, and legal defense trail — generated before the patient leaves the room.',
      },
      {
        k: 'Compliance deadlines, tracked automatically',
        v: 'Direct Access notification windows, pending referrals, and claim filing deadlines — all tracked in real time with a live Liability Score.',
      },
    ],
  },
]

export function HowTabs() {
  const [active, setActive] = useState(1)

  return (
    <>
      <div className="flex flex-wrap items-end justify-between gap-6">
        <h2 className="max-w-xl text-[clamp(1.8rem,3.5vw,2.6rem)] font-bold tracking-[-0.02em]">
          From blind spot to documented proof.
        </h2>
        <div className="inline-flex rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] p-1">
          {tabs.map((t, i) => (
            <button
              key={t.id}
              onClick={() => setActive(i)}
              className={[
                'rounded-lg px-4 py-2 text-[14px] font-semibold transition',
                active === i
                  ? 'bg-white text-[#0F172A] shadow-sm'
                  : 'text-[#64748B] hover:text-[#0F172A]',
              ].join(' ')}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div key={active} className="fade-up mt-10 grid gap-5 sm:grid-cols-3">
        {tabs[active].steps.map((s, i) => (
          <div key={i} className="relative rounded-2xl border border-[#E2E8F0] bg-white p-6">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#0F172A] text-[14px] font-bold text-white">
              {i + 1}
            </div>
            <div className="mt-4 text-[16px] font-semibold">{s.k}</div>
            <p className="mt-1.5 text-[14px] leading-relaxed text-[#64748B]">{s.v}</p>
          </div>
        ))}
      </div>
    </>
  )
}
