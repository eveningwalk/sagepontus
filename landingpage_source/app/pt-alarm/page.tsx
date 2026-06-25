"use client"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Chrome,
  ClipboardCopy,
  FileText,
  ShieldAlert,
  Zap,
} from "lucide-react"

// ── Red Flag Conditions ─────────────────────────────────────────────
const CONDITIONS = [
  {
    level: "EMERGENCY",
    color: "bg-red-50 border-red-200",
    badgeColor: "bg-red-100 text-red-700",
    icon: "🚨",
    name: "Cauda Equina Syndrome",
    desc: "Saddle anesthesia, bilateral leg weakness, bowel/bladder dysfunction",
  },
  {
    level: "EMERGENCY",
    color: "bg-red-50 border-red-200",
    badgeColor: "bg-red-100 text-red-700",
    icon: "🚨",
    name: "Abdominal Aortic Aneurysm",
    desc: "Pulsating abdominal mass, tearing back pain, vascular risk factors",
  },
  {
    level: "URGENT",
    color: "bg-orange-50 border-orange-200",
    badgeColor: "bg-orange-100 text-orange-700",
    icon: "⚠️",
    name: "Spinal Fracture",
    desc: "Trauma history, steroid use, age >70, point tenderness on percussion",
  },
  {
    level: "URGENT",
    color: "bg-orange-50 border-orange-200",
    badgeColor: "bg-orange-100 text-orange-700",
    icon: "⚠️",
    name: "Spinal Malignancy",
    desc: "Cancer history, unexplained weight loss, constant pain unrelieved by rest",
  },
  {
    level: "URGENT",
    color: "bg-orange-50 border-orange-200",
    badgeColor: "bg-orange-100 text-orange-700",
    icon: "⚠️",
    name: "Spinal Infection",
    desc: "Fever with back pain, recent infection, IV drug use, immune compromise",
  },
  {
    level: "WATCHLIST",
    color: "bg-yellow-50 border-yellow-200",
    badgeColor: "bg-yellow-100 text-yellow-700",
    icon: "🔍",
    name: "Inflammatory Spondyloarthropathy",
    desc: "Age <40, morning stiffness >1hr, improved with exercise, SI joint tenderness",
  },
]

// ── Steps ───────────────────────────────────────────────────────────
const STEPS = [
  {
    num: "01",
    icon: <ClipboardCopy className="w-5 h-5" />,
    title: "Paste SOAP Note",
    desc: "Copy the patient's SOAP note from your EMR. One click pastes it into the Chrome Extension — no typing required.",
  },
  {
    num: "02",
    icon: <Zap className="w-5 h-5" />,
    title: "AI Screens for Red Flags",
    desc: "Goodman's clinical criteria run in under 2 seconds. Six conditions, weighted scoring, negation-aware parsing.",
  },
  {
    num: "03",
    icon: <FileText className="w-5 h-5" />,
    title: "Instant Referral Letter",
    desc: "RED alert auto-generates a physician referral letter. Copy and hand it to the patient before they leave.",
  },
]

// ── Main Page ───────────────────────────────────────────────────────
const PT_APP_URL = process.env.NEXT_PUBLIC_PT_APP_URL ?? ""

export default function PtAlarmPage() {
  return (
    <div className="min-h-screen bg-background text-foreground">

      {/* ── Minimal Header ─────────────────────────────────────── */}
      <header className="sticky top-0 z-50 border-b border-border bg-background/95 backdrop-blur">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-red-600" />
            <span className="font-bold text-sm">Sage Pontus <span className="text-red-600">PT Red Flag</span></span>
          </div>
          <div className="flex items-center gap-2">
            <a
              href={`${process.env.NEXT_PUBLIC_PT_APP_URL ?? ""}/pt/login/`}
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Sign in
            </a>
            <a href={`${PT_APP_URL}/pt/signup/`}>
              <Button size="sm">Get Early Access</Button>
            </a>
          </div>
        </div>
      </header>

      <main>
        {/* ── Hero ────────────────────────────────────────────── */}
        <section className="relative overflow-hidden py-24 px-4 sm:px-6 lg:px-8">
          {/* background blobs */}
          <div className="absolute -top-40 -right-40 w-96 h-96 rounded-full bg-red-100/40 blur-3xl pointer-events-none" />
          <div className="absolute -bottom-40 -left-40 w-96 h-96 rounded-full bg-indigo-100/30 blur-3xl pointer-events-none" />

          <div className="relative mx-auto max-w-3xl text-center">
            <Badge className="mb-6 bg-red-100 text-red-700 hover:bg-red-100 border-red-200">
              For Physical Therapists
            </Badge>

            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight mb-6 leading-tight">
              Miss a Red Flag Once.
              <br />
              <span className="text-red-600">One Lawsuit Ends Your Clinic.</span>
            </h1>

            <p className="text-lg sm:text-xl text-muted-foreground mb-10 max-w-2xl mx-auto leading-relaxed">
              AI-powered SOAP note screening built on Goodman&apos;s clinical guidelines.
              Detect the 6 serious conditions in under 2 seconds — right inside your EMR workflow.
            </p>

            <div className="flex flex-col sm:flex-row gap-3 justify-center">
              <a href={`${PT_APP_URL}/pt/signup/`}>
                <Button size="lg" className="bg-red-600 hover:bg-red-700 text-white gap-2">
                  Get Early Access <ArrowRight className="w-4 h-4" />
                </Button>
              </a>
              <Button
                size="lg"
                variant="outline"
                className="gap-2"
                onClick={() => document.getElementById("how-it-works")?.scrollIntoView({ behavior: "smooth" })}
              >
                <Chrome className="w-4 h-4" /> How the Extension Works
              </Button>
            </div>

            <p className="mt-6 text-xs text-muted-foreground">
              Built on Goodman & Snyder&apos;s <em>Differential Diagnosis for Physical Therapists</em> · Clipboard-only, no EMR integration required
            </p>
          </div>
        </section>

        {/* ── Alarm Preview Card ─────────────────────────────── */}
        <section className="py-8 px-4 sm:px-6 lg:px-8 bg-muted/30">
          <div className="mx-auto max-w-md">
            <div className="rounded-2xl border-2 border-red-400 bg-red-50 p-5 shadow-lg">
              <div className="flex items-center gap-4 mb-4">
                <span className="text-5xl">🚨</span>
                <div>
                  <div className="text-lg font-black text-red-600">RED ALERT — Immediate Action Required</div>
                  <div className="text-sm text-gray-500 mt-0.5">Cauda Equina Syndrome</div>
                </div>
              </div>
              <div className="text-xs text-red-600 font-semibold bg-red-100 rounded px-3 py-2 mb-3">
                Primary trigger: Saddle anesthesia reported
              </div>
              <ul className="space-y-1 mb-4">
                {["Saddle anesthesia", "Bilateral leg weakness", "Bladder dysfunction"].map((s) => (
                  <li key={s} className="flex items-center gap-2 text-xs text-gray-700">
                    <span className="text-yellow-500">⚑</span> {s}
                  </li>
                ))}
              </ul>
              <div className="flex items-center gap-3">
                <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div className="h-full bg-red-500 rounded-full" style={{ width: "94%" }} />
                </div>
                <span className="text-xs font-bold text-gray-700">94%</span>
              </div>
              <p className="text-xs text-gray-400 mt-1">Risk score</p>
            </div>
            <p className="text-center text-xs text-muted-foreground mt-3">
              Example output — generated from a SOAP note paste
            </p>
          </div>
        </section>

        {/* ── How It Works ──────────────────────────────────────── */}
        <section id="how-it-works" className="py-24 px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-5xl">
            <div className="text-center mb-14">
              <h2 className="text-3xl sm:text-4xl font-bold mb-4">How It Works</h2>
              <p className="text-muted-foreground max-w-xl mx-auto">
                No EMR integration, no API keys, no IT department. Just a Chrome Extension and a paste.
              </p>
            </div>

            <div className="grid sm:grid-cols-3 gap-8">
              {STEPS.map((step) => (
                <div key={step.num} className="relative">
                  <div className="flex items-center gap-3 mb-3">
                    <div className="w-10 h-10 rounded-xl bg-indigo-100 flex items-center justify-center text-indigo-600">
                      {step.icon}
                    </div>
                    <span className="text-2xl font-black text-indigo-200">{step.num}</span>
                  </div>
                  <h3 className="font-semibold text-base mb-2">{step.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{step.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Conditions Covered ────────────────────────────────── */}
        <section className="py-24 px-4 sm:px-6 lg:px-8 bg-muted/30">
          <div className="mx-auto max-w-5xl">
            <div className="text-center mb-14">
              <h2 className="text-3xl sm:text-4xl font-bold mb-4">6 Conditions Covered</h2>
              <p className="text-muted-foreground max-w-xl mx-auto">
                Every condition follows Goodman&apos;s validated screening criteria. EMERGENCY conditions
                are flagged immediately — no wait for a score to accumulate.
              </p>
            </div>

            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {CONDITIONS.map((c) => (
                <div key={c.name} className={`rounded-xl border p-5 ${c.color}`}>
                  <div className="flex items-start justify-between mb-3">
                    <span className="text-2xl">{c.icon}</span>
                    <Badge className={`text-xs font-semibold ${c.badgeColor} border-0`}>
                      {c.level}
                    </Badge>
                  </div>
                  <h3 className="font-bold text-sm mb-1.5">{c.name}</h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">{c.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Why It Matters ────────────────────────────────────── */}
        <section className="py-24 px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-5xl">
            <div className="text-center mb-14">
              <h2 className="text-3xl sm:text-4xl font-bold mb-4">Why This Matters</h2>
            </div>
            <div className="grid sm:grid-cols-3 gap-8 text-center mb-16">
              {[
                { stat: "1 in 5", desc: "PT malpractice cases involve a missed red flag or delayed physician referral" },
                { stat: "< 2 sec", desc: "Time to screen a full SOAP note — faster than reading the O section yourself" },
                { stat: "6 → 1", desc: "Six separate screening protocols consolidated into a single workflow step" },
              ].map((item) => (
                <div key={item.stat} className="p-6 rounded-2xl bg-muted/40 border border-border">
                  <div className="text-4xl font-black text-foreground mb-3">{item.stat}</div>
                  <p className="text-sm text-muted-foreground leading-relaxed">{item.desc}</p>
                </div>
              ))}
            </div>

            <div className="rounded-2xl bg-card border border-border p-8 max-w-2xl mx-auto">
              <h3 className="font-bold text-lg mb-4">For PT Center Directors</h3>
              <ul className="space-y-3">
                {[
                  "Standardize red flag screening across all therapists — not just your senior staff",
                  "Auto-generated referral letters create a documented paper trail for every escalation",
                  "Runs inside the browser — no PHI leaves without the therapist pressing Paste",
                  "Per-patient session history tracks symptom progression across visits",
                ].map((item) => (
                  <li key={item} className="flex items-start gap-3 text-sm">
                    <CheckCircle2 className="w-4 h-4 text-green-500 mt-0.5 shrink-0" />
                    <span className="text-muted-foreground">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        {/* ── CTA ───────────────────────────────────────────────── */}
        <section className="py-24 px-4 sm:px-6 lg:px-8 bg-foreground text-background">
          <div className="mx-auto max-w-2xl text-center">
            <div className="flex justify-center mb-6">
              <AlertTriangle className="w-12 h-12 text-red-400" />
            </div>
            <h2 className="text-3xl sm:text-4xl font-bold mb-4">
              Every SOAP note is a screening opportunity.
            </h2>
            <p className="text-background/70 mb-10 text-lg">
              Join PTs who are building the documentation trail that protects their clinic.
            </p>
            <a href={`${PT_APP_URL}/pt/signup/`}>
              <Button size="lg" className="bg-red-600 hover:bg-red-700 text-white gap-2 text-base">
                Get Early Access <ArrowRight className="w-4 h-4" />
              </Button>
            </a>
            <p className="mt-4 text-xs text-background/50">
              Chrome Extension · Physical Therapy clinics · Limited early access slots
            </p>
          </div>
        </section>
      </main>

      {/* ── Footer ────────────────────────────────────────────── */}
      <footer className="py-8 px-4 border-t border-border">
        <div className="mx-auto max-w-5xl flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-red-600" />
            <span>Sage Pontus PT Red Flag Alert</span>
          </div>
          <p>
            Clinical criteria: Goodman &amp; Snyder,{" "}
            <em>Differential Diagnosis for Physical Therapists</em>, 6th Ed.
          </p>
        </div>
      </footer>

    </div>
  )
}
