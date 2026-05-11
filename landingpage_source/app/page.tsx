"use client"

import { useState } from "react"
import { Header } from "@/components/landing/header"
import { HeroSection } from "@/components/landing/hero-section"
import { ProblemSolutionSection } from "@/components/landing/problem-solution-section"
import { DemoSection } from "@/components/landing/demo-section"
import { FeaturesSection } from "@/components/landing/features-section"
import { TeamSection } from "@/components/landing/team-section"
import { CTASection } from "@/components/landing/cta-section"
import { Footer } from "@/components/landing/footer"
import { SignupModal } from "@/components/landing/signup-modal"

export default function LandingPage() {
  const [signupOpen, setSignupOpen] = useState(false)

  return (
    <div className="min-h-screen bg-background">
      <Header onGetEarlyAccess={() => setSignupOpen(true)} />
      <main>
        <HeroSection onGetEarlyAccess={() => setSignupOpen(true)} />
        <ProblemSolutionSection />
        <DemoSection />
        <FeaturesSection />
        <TeamSection />
        <CTASection onGetEarlyAccess={() => setSignupOpen(true)} />
      </main>
      <Footer />
      <SignupModal open={signupOpen} onOpenChange={setSignupOpen} />
    </div>
  )
}
