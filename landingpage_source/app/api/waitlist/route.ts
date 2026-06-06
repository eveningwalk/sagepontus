import { Resend } from 'resend'
import { NextRequest, NextResponse } from 'next/server'

const AUDIENCE_ID = process.env.RESEND_AUDIENCE_ID || ''
const FROM_EMAIL  = 'SagePontus <waitlist@sagepontus.com>'

const isEmail = (v: string) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(v.trim())

export async function POST(req: NextRequest) {
  const resend = new Resend(process.env.RESEND_API_KEY || 'dummy_key_for_build')
  try {
    const { email, source = 'landing' } = await req.json()

    if (!email || !isEmail(email)) {
      return NextResponse.json({ error: 'Invalid email address.' }, { status: 400 })
    }

    const normalised = email.trim().toLowerCase()

    // 1. Resend Audience에 연락처 추가 (중복이면 update)
    if (AUDIENCE_ID) {
      await resend.contacts.create({
        audienceId: AUDIENCE_ID,
        email:      normalised,
        unsubscribed: false,
      })
    }

    // 2. 확인 이메일 발송
    await resend.emails.send({
      from:    FROM_EMAIL,
      to:      normalised,
      subject: "You’re on the SagePontus waitlist 🛡️",
      html: `
        <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
                    max-width:520px;margin:0 auto;padding:40px 24px;color:#0F172A;">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:32px;">
            <div style="width:36px;height:36px;border-radius:8px;background:#0EA5E9;
                        display:flex;align-items:center;justify-content:center;">
              <span style="color:#fff;font-size:18px;">🛡️</span>
            </div>
            <span style="font-size:18px;font-weight:700;">SagePontus</span>
          </div>

          <h1 style="font-size:24px;font-weight:800;margin:0 0 12px;line-height:1.2;">
            You're on the list.
          </h1>
          <p style="font-size:16px;color:#475569;line-height:1.6;margin:0 0 24px;">
            We'll reach out as soon as beta access opens. Early members get
            <strong>6 months free</strong>.
          </p>

          <div style="background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;
                      padding:20px 24px;margin-bottom:32px;">
            <div style="font-size:13px;font-weight:700;text-transform:uppercase;
                        letter-spacing:.08em;color:#0EA5E9;margin-bottom:12px;">
              What SagePontus does for your clinic
            </div>
            <ul style="margin:0;padding:0 0 0 18px;color:#374151;font-size:14px;line-height:1.8;">
              <li>Flags red flags PTAs miss — before they become your lawsuit</li>
              <li>Generates physician referral letters in seconds</li>
              <li>Tracks compliance deadlines across your entire clinic</li>
            </ul>
          </div>

          <p style="font-size:13px;color:#94A3B8;margin:0;">
            © 2026 SagePontus · Made for clinicians, by clinicians.<br>
            <a href="https://sagepontus.com" style="color:#0EA5E9;text-decoration:none;">sagepontus.com</a>
          </p>
        </div>
      `,
    })

    return NextResponse.json({ ok: true })
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Unknown error'
    console.error('[waitlist]', message)
    return NextResponse.json({ error: 'Failed to join waitlist.' }, { status: 500 })
  }
}
