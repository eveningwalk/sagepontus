import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { MessageSquareText, Workflow, BarChart3, Shield } from "lucide-react"

export function FeaturesSection() {
  const features = [
    {
      icon: MessageSquareText,
      title: "질문 플로우 엔진",
      description: "자연어 기반 질문-응답 체인으로 복잡한 비즈니스 요구사항을 구조화된 실행 계획으로 전환합니다.",
    },
    {
      icon: Workflow,
      title: "Vertical AI 오케스트레이션",
      description: "산업별 맞춤 AI 에이전트가 협업하여 도메인 특화된 고품질 결과물을 생성합니다.",
    },
    {
      icon: BarChart3,
      title: "실시간 인사이트 대시보드",
      description: "전략 실행 현황을 실시간으로 모니터링하고 데이터 기반 의사결정을 지원합니다.",
    },
    {
      icon: Shield,
      title: "엔터프라이즈 보안",
      description: "SOC 2 인증, 데이터 암호화, SSO 지원으로 기업 환경에 최적화된 보안을 제공합니다.",
    },
  ]

  return (
    <section id="features" className="py-24 px-4 sm:px-6 lg:px-8 bg-muted/30">
      <div className="mx-auto max-w-6xl">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-4">
            Key Features
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            전략과 실행의 간극을 메우는 핵심 기능들
          </p>
        </div>

        <div className="grid sm:grid-cols-2 gap-6">
          {features.map((feature, index) => (
            <Card key={index} className="bg-card border-border hover:border-primary/30 transition-colors group">
              <CardHeader>
                <div className="w-12 h-12 rounded-xl bg-primary/10 flex items-center justify-center mb-4 group-hover:bg-primary/20 transition-colors">
                  <feature.icon className="w-6 h-6 text-primary" />
                </div>
                <CardTitle className="text-xl text-foreground">{feature.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription className="text-base text-muted-foreground leading-relaxed">
                  {feature.description}
                </CardDescription>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}
