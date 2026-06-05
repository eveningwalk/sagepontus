'use client'

import { useState } from 'react'

const tabs = [
  {
    id: 'ptas',
    label: 'For PTAs',
    steps: [
      {
        k: 'No new workflow required',
        v: 'Capture the session, any way you work. Paste a note, or upload a file — SagePontus works with however your clinic already documents.',
      },
      {
        k: 'SagePontus screens in real time',
        v: "Every symptom is cross-checked against Goodman's 6 red flag criteria.",
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
        k: 'Screening proof, not just session notes',
        v: "Every red flag screening is timestamped and stored. When a lawyer asks 'did you screen?' — you have a record, not a memory.",
      },
      {
        k: 'From red flag to documentation — in seconds',
        v: 'When a red flag fires, SagePontus generates the physician referral letter, medical necessity documentation, insurance appeal, and legal defense trail — before the patient leaves the room.',
      },
      {
        k: 'Liability Score, not gut feeling',
        v: 'Track every Direct Access deadline, open red flag, and pending referral across your entire clinic — with a live Liability Score that tells you your exposure before the insurer does.',
      },
    ],
  },
]

export function HowTabs() {
  const [active, setActive] = useState(0)

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
