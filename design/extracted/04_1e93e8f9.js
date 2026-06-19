/* Shared content, icon helper, and small utilities for all 5 variants */
const { useState, useEffect, useRef, useCallback, useMemo } = React;

const cx = (...a) => a.filter(Boolean).join(" ");

/* Lucide icon as a React-safe component (manages its own DOM subtree) */
function Icon({ name, size = 20, stroke = 2, className = "", style = {} }) {
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current;
    if (!el || !window.lucide) return;
    el.innerHTML = "";
    const i = document.createElement("i");
    i.setAttribute("data-lucide", name);
    i.setAttribute("width", size);
    i.setAttribute("height", size);
    i.setAttribute("stroke-width", stroke);
    el.appendChild(i);
    try { window.lucide.createIcons(); } catch (e) {}
  }, [name, size, stroke]);
  return <span ref={ref} className={className} style={{ display: "inline-flex", lineHeight: 0, ...style }} aria-hidden="true" />;
}

/* email validation */
const isEmail = (v) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(v).trim());

const CONTENT = {
  brand: "SagePontus",
  tagline: "AI charting for physical therapists",
  hero: {
    eyebrow: "Chrome extension · Private beta",
    headline: ["Your PTA Missed a Red Flag.", "You Just Inherited a $134K Lawsuit."],
    sub: "Direct Access gave PTAs more power. It also gave YOU more liability. SagePontus flags what humans miss — before it becomes your problem.",
    cta: "Join the Waitlist",
    trust: "Free during beta · No credit card · Works with WebPT",
  },
  pains: [
    { icon: "gavel", brand: 2, stat: "$134K", title: "Average PT Malpractice Lawsuit", body: "PT is the #1 medical field for malpractice claims. Your PTA's blind spot is your legal exposure." },
    { icon: "trending-down", brand: 0, stat: "$47K/yr", title: "Lost to Documentation Overhead", body: "Every hour spent on paperwork is an hour not treating — and revenue quietly walking out the door." },
    { icon: "shield-x", brand: 1, stat: "Zero Notice", title: "Before Medicare Exclusion", body: "A single PTA supervision violation can trigger repayment demands, penalties, and full Medicare exclusion. Most clinics don't know until it's too late." },
  ],
  how: {
    tabs: [
      {
        id: "ptas", label: "For PTAs",
        steps: [
          { k: "No new workflow required", v: "Capture the session, any way you work. Paste a note, or upload a file — SagePontus works with however your clinic already documents." },
          { k: "SagePontus screens in real time", v: "Every symptom is cross-checked against Goodman's 6 red flag criteria." },
          { k: "Flagged or cleared — instantly", v: "If a red flag fires, a physician referral letter is ready before the patient leaves the room. If not, the session is documented and closed." },
        ],
      },
      {
        id: "directors", label: "For Clinic Directors",
        steps: [
          { k: "Screening proof, not just session notes", v: "Every red flag screening is timestamped and stored separately from your SOAP note. When a lawyer asks 'did you screen?' — you have a record, not a memory." },
          { k: "From red flag to documentation — in seconds", v: "When a red flag fires, SagePontus generates the physician referral letter, medical necessity documentation, insurance appeal, and legal defense trail — before the patient leaves the room." },
          { k: "Real-time liability dashboard", v: "See every open alert, pending referral, and follow-up status across your entire clinic. Know your exposure before the insurer does." },
        ],
      },
    ],
  },
  features: [
    {
      icon: "shield-alert", spark: true,
      title: "The Malpractice Shield",
      body: "Instantly scans session notes against 50+ clinical patterns (Goodman's Guidelines) to catch hidden cancer, fractures, or vascular emergencies before liability strikes.",
      tag: "For Clinic Directors",
    },
    {
      icon: "clipboard-check",
      title: "Screening proof, not just session notes",
      body: "Every red flag screening is timestamped and stored. When a lawyer asks 'did you screen?' — you have a record, not a memory.",
      tag: "For Clinic Directors",
    },
    {
      icon: "file-signature",
      title: "Audit-Proof Referral Generator",
      body: "Physician referral and medical necessity letters generated in seconds. Backed by clinical evidence that MDs respect — and keeps your clinic off the Medicare audit list.",
      tag: "For Clinic Directors",
    },
  ],
  proof: {
    line: "Trusted by early-access PTs across California, Texas, and Florida",
    people: [
      { initials: "RM", name: "Dr. Rivera", role: "DPT · Austin, TX" },
      { initials: "JL", name: "J. Lin", role: "Clinic Director · San Diego, CA" },
      { initials: "AK", name: "A. Kaur", role: "PTA · Miami, FL" },
    ],
    states: ["California", "Texas", "Florida"],
  },
  finalCta: {
    headline: "Be first when we launch.",
    sub: "Beta access is limited. Early members get 6 months free.",
  },
  footer: "© 2026 SagePontus · For Physical Therapists",
  emrs: ["WebPT", "Prompt EMR", "Jane", "Raintree", "TheraOffice", "Other / paper"],
  soap: {
    S: "Pt reports 4/10 lumbar pain, down from 7/10 at last visit. Denies numbness, tingling, or bowel/bladder changes. Sleeping through the night again.",
    O: "Lumbar AROM: flexion 60° (was 45°), extension 20°. (+) tolerance to manual therapy. Performed therapeutic exercise x3 sets, lumbar stabilization.",
    A: "Improving s/p lumbar strain. Pt tolerating progression well with measurable AROM and pain gains. No red flags noted this session.",
    P: "Continue 2x/week x3 weeks. Progress core stabilization and add functional lifting mechanics. Re-assess outcome measures next visit.",
  },
};

Object.assign(window, { Icon, CONTENT, cx, isEmail });
