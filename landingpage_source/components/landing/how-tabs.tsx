'use client'

import { useState } from 'react'

const tabs = [
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
  {
    id: 'ptas',
    label: 'For PTs & PTAs',
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
        v: "If a red flag fires, a physician referral letter is ready before the patient leaves the room. If not, the screening is recorded and the session closes clean.",
      },
    ],
  },
]

export function HowTabs() {
  const [active, setActive] = useState(0)

  return (
    <>
      {/* h2 — centered (matches reference Heading with center prop) */}
      <h2 className="text-center mx-auto max-w-xl font-display text-[clamp(1.8rem,3.5vw,2.6rem)] font-bold tracking-[-0.02em]">
        From blind spot to documented proof.
      </h2>

      {/* tablist — left-aligned, same as reference Tabs component top */}
      <div
        className="mt-6 inline-flex rounded-lg border border-slate-200 bg-white p-1 gap-1"
        role="tablist"
      >
        {tabs.map((t, i) => (
          <button
            key={t.id}
            role="tab"
            aria-selected={active === i}
            onClick={() => setActive(i)}
            className={
              active === i
                ? 'px-5 py-2.5 rounded-md text-sm font-semibold bg-slate-900 text-white transition'
                : 'px-5 py-2.5 rounded-md text-sm font-semibold text-slate-500 hover:text-slate-900 transition'
            }
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* step grid — exact reference authority stepGrid */}
      <div
        key={active}
        className="mt-10 grid gap-px md:grid-cols-3 overflow-hidden rounded-xl border border-slate-200 bg-slate-200"
      >
        {tabs[active].steps.map((s, i) => (
          <div key={i} className="h-full bg-white p-7">
            <div className="font-display text-2xl font-bold text-slate-200">
              {String(i + 1).padStart(2, '0')}
            </div>
            <div className="font-display mt-2 text-lg font-semibold text-slate-900 leading-snug">{s.k}</div>
            <p className="mt-2 text-[15px] leading-relaxed text-slate-600">{s.v}</p>
          </div>
        ))}
      </div>
    </>
  )
}
