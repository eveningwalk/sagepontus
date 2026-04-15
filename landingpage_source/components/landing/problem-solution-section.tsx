import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { X, Check, ArrowRight } from "lucide-react"

export function ProblemSolutionSection() {
  const beforeItems = [
    "전략 문서가 실행으로 이어지지 않음",
    "팀 간 커뮤니케이션 단절",
    "반복적인 수작업 프로세스",
    "데이터 기반 의사결정의 어려움",
  ]

  const afterItems = [
    "질문 플로우로 전략 → 실행 자동 연결",
    "AI가 팀 간 컨텍스트 자동 공유",
    "반복 업무 자동화로 시간 절약",
    "실시간 인사이트로 빠른 의사결정",
  ]

  return (
    <section className="py-24 px-4 sm:px-6 lg:px-8 bg-muted/30">
      <div className="mx-auto max-w-6xl">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-4">
            Why Sage Pontus?
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            전략과 실행 사이의 간극을 AI로 연결합니다
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-6 lg:gap-8 items-start">
          <Card className="border-destructive/20 bg-card shadow-sm">
            <CardHeader className="pb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-destructive/10 flex items-center justify-center">
                  <X className="w-5 h-5 text-destructive" />
                </div>
                <CardTitle className="text-xl text-foreground">Before Sage Pontus</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <ul className="space-y-4">
                {beforeItems.map((item, index) => (
                  <li key={index} className="flex items-start gap-3">
                    <div className="mt-1 w-5 h-5 rounded-full bg-destructive/10 flex items-center justify-center shrink-0">
                      <X className="w-3 h-3 text-destructive" />
                    </div>
                    <span className="text-muted-foreground">{item}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          <Card className="border-primary/20 bg-card shadow-sm relative">
            <div className="absolute -left-3 top-1/2 -translate-y-1/2 hidden lg:flex">
              <div className="w-6 h-6 rounded-full bg-primary flex items-center justify-center">
                <ArrowRight className="w-3 h-3 text-primary-foreground" />
              </div>
            </div>
            <CardHeader className="pb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                  <Check className="w-5 h-5 text-primary" />
                </div>
                <CardTitle className="text-xl text-foreground">After Sage Pontus</CardTitle>
              </div>
            </CardHeader>
            <CardContent>
              <ul className="space-y-4">
                {afterItems.map((item, index) => (
                  <li key={index} className="flex items-start gap-3">
                    <div className="mt-1 w-5 h-5 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                      <Check className="w-3 h-3 text-primary" />
                    </div>
                    <span className="text-foreground">{item}</span>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>

        <div className="mt-16 grid grid-cols-2 lg:grid-cols-4 gap-6">
          {[
            { value: "80%", label: "시간 절약" },
            { value: "3x", label: "생산성 향상" },
            { value: "95%", label: "정확도" },
            { value: "24/7", label: "운영 지원" },
          ].map((stat, index) => (
            <div key={index} className="text-center p-6 rounded-xl bg-card border border-border">
              <div className="text-3xl sm:text-4xl font-bold text-primary mb-2">{stat.value}</div>
              <div className="text-sm text-muted-foreground">{stat.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
