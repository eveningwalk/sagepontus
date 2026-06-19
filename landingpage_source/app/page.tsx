import type { Metadata } from 'next'
import { SeoPage } from '@/components/landing/seo-page'

export const metadata: Metadata = {
  title: 'SagePontus | PT Red Flag Screening & Compliance Shield',
  description: "Protect your physical therapy clinic from malpractice lawsuits and claim denials. SagePontus screens Goodman's 6 criteria in real time.",
}

export default function LandingPage() {
  return <SeoPage />
}
