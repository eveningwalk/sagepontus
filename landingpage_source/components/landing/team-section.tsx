import { Card, CardContent } from "@/components/ui/card"
import { Award, Building2, Users } from "lucide-react"

export function TeamSection() {
  const credentials = [
    {
      icon: Building2,
      title: "전문 경험",
      description: "글로벌 컨설팅 펌과 테크 기업 출신 전문가들이 만들었습니다.",
    },
    {
      icon: Award,
      title: "검증된 기술력",
      description: "AI/ML 분야 10년 이상의 연구개발 경험을 보유하고 있습니다.",
    },
    {
      icon: Users,
      title: "고객 중심",
      description: "50+ 기업 고객과 함께 실제 비즈니스 문제를 해결해왔습니다.",
    },
  ]

  return (
    <section id="team" className="py-24 px-4 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-4">
            Trusted by Industry Leaders
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            기업의 디지털 전환을 함께하는 신뢰할 수 있는 파트너
          </p>
        </div>

        <div className="grid sm:grid-cols-3 gap-6 mb-16">
          {credentials.map((item, index) => (
            <Card key={index} className="bg-card border-border text-center">
              <CardContent className="pt-8 pb-6">
                <div className="w-14 h-14 rounded-2xl bg-secondary/10 flex items-center justify-center mx-auto mb-4">
                  <item.icon className="w-7 h-7 text-secondary" />
                </div>
                <h3 className="font-semibold text-foreground text-lg mb-2">{item.title}</h3>
                <p className="text-muted-foreground text-sm leading-relaxed">{item.description}</p>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="bg-card rounded-2xl border border-border p-8 lg:p-12">
          <div className="flex flex-col lg:flex-row items-center gap-8 lg:gap-12">
            <div className="flex-1 text-center lg:text-left">
              <blockquote className="text-xl lg:text-2xl text-foreground font-medium mb-6 leading-relaxed">
                {`"Sage Pontus는 우리 팀의 전략 실행 방식을 완전히 바꿔놓았습니다. 
                이제 아이디어에서 실행까지의 시간이 절반으로 줄었습니다."`}
              </blockquote>
              <div className="flex items-center justify-center lg:justify-start gap-4">
                <div className="w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                  <span className="text-primary font-bold">KL</span>
                </div>
                <div className="text-left">
                  <p className="font-semibold text-foreground">김리더</p>
                  <p className="text-sm text-muted-foreground">전략기획팀장, 테크 스타트업</p>
                </div>
              </div>
            </div>
            
            <div className="hidden lg:block w-px h-32 bg-border" />
            
            <div className="grid grid-cols-2 gap-8">
              <div className="text-center">
                <p className="text-4xl font-bold text-primary mb-1">50+</p>
                <p className="text-sm text-muted-foreground">Enterprise Clients</p>
              </div>
              <div className="text-center">
                <p className="text-4xl font-bold text-secondary mb-1">99%</p>
                <p className="text-sm text-muted-foreground">Customer Satisfaction</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
