import { Header } from "@/components/landing/header"
import { HeroSection } from "@/components/landing/hero-section"
import { ProblemSolutionSection } from "@/components/landing/problem-solution-section"
import { DemoSection } from "@/components/landing/demo-section"
import { FeaturesSection } from "@/components/landing/features-section"
import { TeamSection } from "@/components/landing/team-section"
import { CTASection } from "@/components/landing/cta-section"
import { Footer } from "@/components/landing/footer"

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main>
        <HeroSection />
        <ProblemSolutionSection />
        <DemoSection />
        <FeaturesSection />
        <TeamSection />
        <CTASection />
      </main>
      <Footer />
    </div>
  )
}
