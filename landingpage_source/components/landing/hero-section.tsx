"use client"

import { Button } from "@/components/ui/button"
import { ArrowRight, Sparkles } from "lucide-react"

const HERO_HEADLINE_1 = "\uC804\uB7B5\uC744 \uC2E4\uBB34 \uACB0\uACFC\uB85C"
const HERO_HEADLINE_2 = "\uC5F0\uACB0\uD558\uB294 AI"
const HERO_DESCRIPTION = "\uC9C8\uBB38 \uD50C\uB85C\uC6B0 \uAE30\uBC18 \uD504\uB86C\uD504\uD2B8\uB85C \uAE30\uC5C5\uC758 \uC804\uB7B5\uC801 \uBE44\uC804\uC744 \uAD6C\uCCB4\uC801\uC778 \uC2E4\uD589 \uACB0\uACFC\uBB3C\uB85C \uC804\uD658\uD569\uB2C8\uB2E4. \uBCF5\uC7A1\uD55C \uBE44\uC988\uB2C8\uC2A4 \uC758\uC0AC\uACB0\uC815\uC744 \uBA85\uD655\uD55C \uC561\uC158\uC73C\uB85C \uB9CC\uB4E4\uC5B4 \uB4DC\uB9BD\uB2C8\uB2E4."

export function HeroSection() {
  return (
    <section className="relative pt-32 pb-20 px-4 sm:px-6 lg:px-8 overflow-hidden">
      <div className="absolute inset-0 -z-10">
        <div className="absolute top-20 left-1/4 w-72 h-72 bg-primary/10 rounded-full blur-3xl" />
        <div className="absolute bottom-20 right-1/4 w-96 h-96 bg-secondary/10 rounded-full blur-3xl" />
      </div>

      <div className="mx-auto max-w-4xl text-center">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-muted border border-border mb-8">
          <Sparkles className="w-4 h-4 text-primary" />
          <span className="text-sm font-medium text-muted-foreground">Vertical AI Orchestration OS</span>
        </div>

        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight text-foreground mb-6 text-balance">
          {HERO_HEADLINE_1}
          <br />
          <span className="text-primary">{HERO_HEADLINE_2}</span>
        </h1>

        <p className="text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto mb-10 leading-relaxed text-pretty">
          {HERO_DESCRIPTION}
        </p>

        <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
          <Button size="lg" className="bg-primary hover:bg-primary/90 text-primary-foreground px-8 h-12 text-base">
            Get Early Access
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
          <Button variant="outline" size="lg" className="px-8 h-12 text-base border-border">
            Watch Demo
          </Button>
        </div>

        <div className="mt-16 flex flex-wrap items-center justify-center gap-8 text-muted-foreground">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-primary" />
            <span className="text-sm">SOC 2 Compliant</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-primary" />
            <span className="text-sm">Enterprise Ready</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-primary" />
            <span className="text-sm">No-Code Setup</span>
          </div>
        </div>
      </div>
    </section>
  )
}
