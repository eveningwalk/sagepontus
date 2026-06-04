/* Variant 1 — Minimal Tech-Premium (white, sky/teal) */
const { useState: useState1, useRef: useRef1, useEffect: useEffect1 } = React;

/* "Liability vs Protection" live shield demo */
function ShieldMockV1() {
  const [pct, setPct] = useState1(0);
  const [done, setDone] = useState1(false);
  const [sent, setSent] = useState1(false);
  useEffect1(() => {
    setPct(0); setDone(false); setSent(false);
    const start = Date.now();
    const id = setInterval(() => {
      const t = Math.min(1, (Date.now() - start) / 2400);
      setPct(Math.round(t * 100));
      if (t >= 1) { clearInterval(id); setDone(true); }
    }, 40);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="reveal mt-14 overflow-hidden rounded-2xl border border-[#E2E8F0] bg-white shadow-[0_30px_80px_-40px_rgba(15,23,42,0.45)]" style={{ animationDelay: "0.25s" }}>
      {/* browser chrome */}
      <div className="flex items-center gap-2 border-b border-[#E2E8F0] bg-[#F8FAFC] px-4 py-3">
        <span className="h-2.5 w-2.5 rounded-full bg-[#E2E8F0]" /><span className="h-2.5 w-2.5 rounded-full bg-[#E2E8F0]" /><span className="h-2.5 w-2.5 rounded-full bg-[#E2E8F0]" />
        <span className="ml-3 flex items-center gap-1.5 text-[12.5px] text-[#94A3B8]"><window.Icon name="lock" size={12} /> app.webpt.com</span>
        <span className="ml-auto flex items-center gap-1.5 rounded-md bg-[#0EA5E9]/10 px-2 py-1 text-[12px] font-semibold text-[#0EA5E9]"><window.Icon name="shield-check" size={12} /> SagePontus</span>
      </div>

      <div className="grid sm:grid-cols-[0.92fr_1.08fr]">
        {/* LEFT — the liability */}
        <div className="bg-white p-6">
          <div className="flex items-center gap-2 text-[12px] font-bold uppercase tracking-wide text-[#B45309]">
            <span>⚠️</span> PTA's Unprocessed Chart
          </div>
          <div className="mt-1 text-[11.5px] text-[#A8A29E]">Daily note · copy-pasted · unscreened</div>
          <div className="mt-4 rounded-xl border border-[#FCD9A8] bg-[#FFFBEB] p-4 font-mono text-[12.5px] leading-relaxed text-[#78716C]">
            "Patient complains of lower back pain, rated 6/10. Performed routine lumbar extensions. Will follow up."
          </div>
          <div className="mt-3 flex items-center gap-1.5 text-[12px] font-medium text-[#B45309]">
            <window.Icon name="triangle-alert" size={13} /> Saved to EMR as-is — no red-flag screening
          </div>
        </div>

        {/* RIGHT — the protection */}
        <div className="bg-[#0F172A] p-6 text-white">
          <div className="flex items-center gap-2 text-[12px] font-bold uppercase tracking-wide text-[#38BDF8]">
            <span>🛡️</span> SagePontus Live Legal Shield
          </div>

          {!done ? (
            <div className="mt-5">
              <div className="flex items-center gap-2 text-[13px] font-medium text-[#7DD3FC]">
                <span className="spin inline-block"><window.Icon name="loader" size={14} /></span> Screening against 50+ Goodman's patterns…
              </div>
              <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-white/10">
                <div className="h-full rounded-full bg-gradient-to-r from-[#0EA5E9] to-[#14B8A6] transition-[width] duration-75" style={{ width: pct + "%" }} />
              </div>
              <div className="mt-2 text-right font-mono text-[11.5px] text-[#64748B]">{pct}%</div>
            </div>
          ) : (
            <div className="mt-4 space-y-3" style={{ animation: "revealUp 0.5s cubic-bezier(0.16,1,0.3,1) both" }}>
              {/* red alert */}
              <div className="rounded-xl border border-[#F43F5E]/45 bg-[#F43F5E]/12 p-3.5">
                <div className="flex items-center gap-2 text-[11.5px] font-bold uppercase tracking-wide text-[#FDA4AF]">
                  <span>🚨</span> Red Flag Detected
                </div>
                <p className="mt-1.5 text-[13px] font-medium leading-snug text-white">
                  Cauda Equina / Progressive Night Pain pattern flag <span className="font-normal text-[#94A3B8]">(Goodman's Guidelines)</span>
                </p>
              </div>

              {/* referral letter card */}
              <div className="rounded-xl border border-white/10 bg-white/[0.045] p-4">
                <div className="flex items-start gap-3">
                  <span className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-gradient-to-br from-[#0EA5E9] to-[#14B8A6] text-white"><window.Icon name="file-signature" size={19} /></span>
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-[13.5px] font-semibold text-white">Physician Referral Letter</span>
                      <span className="rounded bg-white/10 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-[#7DD3FC]">PDF</span>
                    </div>
                    <div className="text-[12px] text-[#94A3B8]">Auto-generated · addressed to Dr. Evans</div>
                  </div>
                  <span className="ml-auto flex shrink-0 items-center gap-1 rounded-full bg-[#10B981]/15 px-2 py-1 text-[11px] font-semibold text-[#6EE7B7]"><window.Icon name="check" size={11} stroke={3} /> Ready to sign</span>
                </div>
                <div className="mt-3.5 rounded-lg border border-white/8 bg-[#0B1220] p-3 text-[11.5px] leading-relaxed text-[#CBD5E1]">
                  <span className="text-[#64748B]">Re:</span> Urgent specialist referral — suspected cauda equina syndrome. Clinical reasoning &amp; outcome data attached per payer requirements.
                  <div className="mt-2 space-y-1.5">
                    <div className="h-1.5 w-full rounded bg-white/8" />
                    <div className="h-1.5 w-4/5 rounded bg-white/8" />
                  </div>
                </div>
                <div className="mt-4 flex gap-2">
                  <button className="inline-flex h-9 flex-1 items-center justify-center gap-1.5 rounded-lg bg-[#0EA5E9] text-[13px] font-semibold text-white transition hover:bg-[#0284C7] active:scale-[0.98]"><window.Icon name="pen-line" size={14} /> Review &amp; sign</button>
                  <button onClick={() => setSent(true)} className={cx("inline-flex h-9 items-center justify-center gap-1.5 rounded-lg px-3.5 text-[13px] font-semibold transition active:scale-[0.98]", sent ? "bg-[#10B981]/15 text-[#6EE7B7]" : "border border-white/15 text-white hover:bg-white/5")}>
                    {sent ? <><window.Icon name="check" size={14} stroke={3} /> Sent</> : <><window.Icon name="send" size={14} /> Send</>}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function WaitlistInlineV1({ size = "lg" }) {
  const [email, setEmail] = useState1("");
  const [state, setState] = useState1("idle"); // idle | error | done
  const submit = (e) => {
    e.preventDefault();
    if (!window.isEmail(email)) { setState("error"); return; }
    setState("done");
  };
  if (state === "done") {
    return (
      <div className="inline-flex items-center gap-3 rounded-xl border border-[#14B8A6]/30 bg-[#14B8A6]/8 px-4 py-3"
           style={{ animation: "popIn 0.5s cubic-bezier(0.16,1,0.3,1) both" }}>
        <span className="grid h-7 w-7 place-items-center rounded-full bg-[#14B8A6] text-white">
          <window.Icon name="check" size={16} stroke={3} />
        </span>
        <div className="text-left">
          <div className="text-[15px] font-semibold text-[#0F172A]">Check your inbox for your access code</div>
          <div className="text-[13px] text-[#64748B]">Sent to {email}</div>
        </div>
      </div>
    );
  }
  return (
    <form onSubmit={submit} className="w-full">
      <div className={cx("flex flex-col gap-2 sm:flex-row sm:items-center",
        state === "error" ? "" : "")}>
        <div className="relative flex-1">
          <input
            type="email" value={email}
            onChange={(e) => { setEmail(e.target.value); if (state === "error") setState("idle"); }}
            placeholder="you@clinic.com"
            className={cx(
              "h-12 w-full rounded-xl border bg-white px-4 text-[15px] text-[#0F172A] outline-none transition placeholder:text-[#94A3B8]",
              state === "error" ? "border-red-400 ring-2 ring-red-100" : "border-[#E2E8F0] focus:border-[#0EA5E9] focus:ring-2 focus:ring-[#0EA5E9]/15"
            )} />
        </div>
        <button type="submit"
          className="group inline-flex h-12 items-center justify-center gap-2 rounded-xl bg-[#0EA5E9] px-5 text-[15px] font-semibold text-white shadow-[0_8px_24px_-8px_rgba(14,165,233,0.6)] transition hover:bg-[#0284C7] active:scale-[0.98]">
          {CONTENT.hero.cta}
          <window.Icon name="arrow-right" size={17} className="transition-transform group-hover:translate-x-0.5" />
        </button>
      </div>
      <div className="mt-2 h-4 text-[13px] text-red-500">
        {state === "error" ? "Please enter a valid work email." : ""}
      </div>
    </form>
  );
}

function SectionLabelV1({ children }) {
  return <div className="mb-3 text-[13px] font-semibold uppercase tracking-[0.14em] text-[#0EA5E9]">{children}</div>;
}

function Variant1() {
  const [tab, setTab] = useState1(0);
  const C = CONTENT;
  return (
    <div className="font-hanken min-h-screen bg-white text-[#0F172A]">
      {/* nav */}
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 pt-28 pb-2">
        <div className="flex items-center gap-2.5">
          <img src="logos/sagepontus-lockup.png" alt="Sagepontus" className="h-8 w-auto" />
        </div>
        <div className="hidden items-center gap-7 text-[14px] font-medium text-[#475569] sm:flex">
          <span className="cursor-pointer hover:text-[#0F172A]">Product</span>
          <span className="cursor-pointer hover:text-[#0F172A]">Safety</span>
          <span className="cursor-pointer hover:text-[#0F172A]">Pricing</span>
          <span className="cursor-pointer rounded-lg border border-[#E2E8F0] px-3 py-1.5 hover:border-[#0EA5E9] hover:text-[#0EA5E9]">Sign in</span>
        </div>
      </header>

      {/* hero */}
      <section className="mx-auto max-w-6xl px-6 pt-16 pb-20">
        <div className="reveal inline-flex items-center gap-2 rounded-full border border-[#E2E8F0] bg-[#F8FAFC] px-3 py-1.5 text-[13px] font-medium text-[#475569]">
          <span className="h-1.5 w-1.5 rounded-full bg-[#14B8A6]" /> {C.hero.eyebrow}
        </div>
        <h1 className="reveal mt-6 max-w-3xl text-[clamp(2.4rem,6vw,4.2rem)] font-extrabold leading-[1.02] tracking-[-0.03em]" style={{ animationDelay: "0.05s" }}>
          {C.hero.headline[0]}<br />
          <span className="bg-gradient-to-r from-[#0EA5E9] to-[#14B8A6] bg-clip-text text-transparent">{C.hero.headline[1]}</span>
        </h1>
        <p className="reveal mt-6 max-w-2xl text-[19px] leading-relaxed text-[#475569]" style={{ animationDelay: "0.1s" }}>{C.hero.sub}</p>
        <div className="reveal mt-8 max-w-xl" style={{ animationDelay: "0.15s" }}><WaitlistInlineV1 /></div>
        <div className="reveal -mt-1 flex items-center gap-2 text-[13.5px] text-[#64748B]" style={{ animationDelay: "0.2s" }}>
          <window.Icon name="check-circle-2" size={15} className="text-[#14B8A6]" /> {C.hero.trust}
        </div>

        {/* product glass mock — PTA notes vs SagePontus analysis */}
        <div className="reveal mt-14 overflow-hidden rounded-2xl border border-[#E2E8F0] bg-[#F8FAFC] shadow-[0_30px_80px_-40px_rgba(15,23,42,0.4)]" style={{ animationDelay: "0.25s" }}>
          <div className="flex items-center gap-2 border-b border-[#E2E8F0] px-4 py-3">
            <span className="h-2.5 w-2.5 rounded-full bg-[#E2E8F0]" /><span className="h-2.5 w-2.5 rounded-full bg-[#E2E8F0]" /><span className="h-2.5 w-2.5 rounded-full bg-[#E2E8F0]" />
            <span className="ml-auto flex items-center gap-1.5 rounded-md bg-[#0EA5E9]/10 px-2 py-1 text-[12px] font-semibold text-[#0EA5E9]"><img src="logos/sagepontus-mark.png" alt="" className="h-3.5 w-3.5 object-contain" /> ✦ SagePontus</span>
          </div>
          <div className="grid md:grid-cols-[45fr_55fr]">
            {/* LEFT — PTA session notes */}
            <div className="bg-white p-6">
              <div className="text-[12px] font-semibold uppercase tracking-wide text-[#94A3B8]">PTA Session in Progress</div>
              <div className="mt-3 rounded-lg border border-[#E2E8F0] bg-[#F8FAFC] px-3 py-2 text-[13px]">
                <span className="font-semibold text-[#0F172A]">Patient:</span> <span className="text-[#475569]">John D. · 58M, lumbar pain</span>
              </div>
              <div className="mt-3 space-y-2.5 text-[13.5px] leading-relaxed">
                <p><span className="font-bold text-[#0F172A]">S:</span> <span className="text-[#64748B]">Pain 4/10, down from 7/10. Flexion 60°</span></p>
                <p><span className="font-bold text-[#0F172A]">O:</span> <span className="text-[#64748B]">AROM improving. Tolerating progression well.</span></p>
                <p><span className="font-bold text-[#0F172A]">A:</span> <span className="text-[#64748B]">Improving s/p lumbar strain.</span></p>
              </div>
              <div className="mt-5 flex items-center gap-1.5 text-[13px] font-medium text-[#0EA5E9]" style={{ animation: "softBlink 1.6s ease-in-out infinite" }}>
                <span>✦</span> Generating next session plan…
              </div>
            </div>
            {/* RIGHT — SagePontus analysis (dark contrast) */}
            <div className="relative bg-[#0F172A] p-6">
              <span className="absolute left-0 top-0 hidden h-full w-px bg-gradient-to-b from-transparent via-[#0EA5E9]/55 to-transparent md:block" />
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-[12px] font-semibold uppercase tracking-wide text-[#38BDF8]"><img src="logos/sagepontus-mark.png" alt="" className="h-3.5 w-3.5 object-contain" /> SagePontus Analysis</div>
                <span className="text-[#FB7185]">⚠️</span>
              </div>
              <div className="relative mt-4 overflow-hidden rounded-xl border border-[#FB7185]/40 bg-[#FB7185]/[0.08] p-4">
                <span className="absolute inset-0 rounded-xl ring-1 ring-[#FB7185]/45" style={{ animation: "softBlink 1.8s ease-in-out infinite" }} />
                <div className="relative flex items-center gap-2 text-[12.5px] font-bold uppercase tracking-wide text-[#FB7185]"><span>⚠️</span> Red Flag Detected</div>
                <p className="relative mt-2.5 text-[13.5px] leading-snug text-white">Age 58 + lumbar pain → <span className="font-semibold text-[#FECDD3]">cardiovascular screen incomplete.</span> Rule out aortic aneurysm before next session.</p>
                <span className="relative mt-3.5 inline-flex items-center gap-1.5 rounded-lg border border-[#FB7185]/20 bg-[#FB7185]/10 px-2.5 py-1 text-[12px] font-semibold text-[#FB7185]">🚨 Physician referral required</span>
              </div>
              <div className="mt-5 flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-4">
                <div className="text-[12.5px]"><span className="text-[#64748B]">Liability exposure:</span> <span className="font-bold text-[#FB7185]">HIGH</span></div>
                <div className="flex items-center gap-2 text-[12.5px]"><span className="text-[#64748B]">Claim status:</span> <span className="inline-block rounded bg-[#1e293b] px-2 py-1 font-mono tracking-wide text-[#FBBF24]">⛔ HOLD</span></div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* pains */}
      <section className="border-y border-[#E2E8F0] bg-[#F8FAFC]">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <SectionLabelV1>The hidden cost</SectionLabelV1>
          <h2 className="max-w-2xl text-[clamp(1.8rem,3.5vw,2.6rem)] font-bold tracking-[-0.02em]">Every clinic loses time and carries risk they can't see.</h2>
          <div className="mt-10 grid gap-5 sm:grid-cols-3">
            {C.pains.map((p, i) => (
              <div key={i} className="rounded-2xl border border-[#E2E8F0] bg-white p-6 transition hover:-translate-y-1 hover:border-[#0EA5E9]/40 hover:shadow-[0_20px_50px_-30px_rgba(14,165,233,0.5)]">
                <span className="grid h-11 w-11 place-items-center rounded-xl bg-[#0EA5E9]/10 text-[#0EA5E9]"><window.BrandPain idx={p.brand} size={26} /></span>
                <div className="mt-5 text-[26px] font-extrabold tracking-tight text-[#0F172A]">{p.stat}</div>
                <div className="text-[15px] font-semibold text-[#0F172A]">{p.title}</div>
                <p className="mt-2 text-[14px] leading-relaxed text-[#64748B]">{p.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* how it works tabs */}
      <section className="mx-auto max-w-6xl px-6 py-20">
        <SectionLabelV1>How it works</SectionLabelV1>
        <div className="flex flex-wrap items-end justify-between gap-6">
          <h2 className="max-w-xl text-[clamp(1.8rem,3.5vw,2.6rem)] font-bold tracking-[-0.02em]">From blind spot to documented proof.</h2>
          <div className="inline-flex rounded-xl border border-[#E2E8F0] bg-[#F8FAFC] p-1">
            {C.how.tabs.map((t, i) => (
              <button key={t.id} onClick={() => setTab(i)}
                className={cx("rounded-lg px-4 py-2 text-[14px] font-semibold transition",
                  tab === i ? "bg-white text-[#0F172A] shadow-sm" : "text-[#64748B] hover:text-[#0F172A]")}>{t.label}</button>
            ))}
          </div>
        </div>
        <div key={tab} className="mt-10 grid gap-5 sm:grid-cols-3" style={{ animation: "fadeUp 0.5s ease both" }}>
          {C.how.tabs[tab].steps.map((s, i) => (
            <div key={i} className="relative rounded-2xl border border-[#E2E8F0] bg-white p-6">
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#0F172A] text-[14px] font-bold text-white">{i + 1}</div>
              <div className="mt-4 text-[16px] font-semibold">{s.k}</div>
              <p className="mt-1.5 text-[14px] leading-relaxed text-[#64748B]">{s.v}</p>
            </div>
          ))}
        </div>
      </section>

      {/* features bento */}
      <section className="border-t border-[#E2E8F0] bg-[#F8FAFC]">
        <div className="mx-auto max-w-6xl px-6 py-20">
          <SectionLabelV1>What you get</SectionLabelV1>
          <h2 className="max-w-2xl text-[clamp(1.8rem,3.5vw,2.6rem)] font-bold tracking-[-0.02em]">Three layers of protection. One extension.</h2>
          <div className="mt-10 grid gap-5 md:grid-cols-3">
            {C.features.map((f, i) => (
              <div key={i} className="group flex flex-col rounded-2xl border border-[#E2E8F0] bg-white p-7 transition hover:-translate-y-1 hover:shadow-[0_24px_60px_-36px_rgba(15,23,42,0.5)]">
                <div className="relative inline-flex">
                  <span className="grid h-12 w-12 place-items-center rounded-xl bg-gradient-to-br from-[#0EA5E9] to-[#14B8A6] text-white shadow-[0_10px_24px_-10px_rgba(14,165,233,0.7)]"><window.Icon name={f.icon} size={22} /></span>
                  {f.spark && <span className="absolute -right-1.5 -top-1.5 grid h-5 w-5 place-items-center rounded-full bg-[#0F172A] text-[#CCFF00]"><window.Icon name="zap" size={11} /></span>}
                </div>
                <h3 className="mt-5 text-[19px] font-bold tracking-tight">{f.title}</h3>
                <p className="mt-2 flex-1 text-[14.5px] leading-relaxed text-[#64748B]">{f.body}</p>
                <span className="mt-5 inline-flex w-fit items-center gap-1.5 rounded-full border border-[#E2E8F0] bg-[#F8FAFC] px-3 py-1 text-[12.5px] font-semibold text-[#475569]"><window.Icon name="users" size={12} /> {f.tag}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* social proof */}
      <section className="mx-auto max-w-6xl px-6 py-16">
        <div className="flex flex-col items-center gap-6 rounded-2xl border border-[#E2E8F0] bg-white p-8 text-center">
          <div className="flex -space-x-3">
            {C.proof.people.map((p, i) => (
              <span key={i} className="grid h-11 w-11 place-items-center rounded-full border-2 border-white bg-gradient-to-br from-[#0EA5E9] to-[#14B8A6] text-[13px] font-bold text-white shadow">{p.initials}</span>
            ))}
          </div>
          <p className="text-[15px] font-medium text-[#475569]">{C.proof.line}</p>
        </div>
      </section>

      {/* final cta */}
      <section className="mx-auto max-w-6xl px-6 pb-24">
        <div className="overflow-hidden rounded-3xl bg-[#0F172A] px-8 py-16 text-center sm:px-16">
          <h2 className="mx-auto max-w-xl text-[clamp(2rem,4vw,3rem)] font-extrabold tracking-[-0.02em] text-white">{C.finalCta.headline}</h2>
          <p className="mx-auto mt-4 max-w-md text-[17px] text-[#94A3B8]">{C.finalCta.sub}</p>
          <div className="mx-auto mt-8 max-w-md text-left"><WaitlistInlineV1 /></div>
        </div>
        <div className="mt-10 flex flex-col items-center justify-between gap-3 text-[13.5px] text-[#94A3B8] sm:flex-row">
          <span>{C.footer}</span>
          <span className="flex items-center gap-2"><img src="logos/sagepontus-shield-outline.png" alt="" className="h-4 w-4 object-contain" /> Made for clinicians, by clinicians.</span>
        </div>
      </section>
    </div>
  );
}

window.Variant1 = Variant1;
