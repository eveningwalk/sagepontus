"use client"

import { Play } from "lucide-react"
import { Button } from "@/components/ui/button"

export function DemoSection() {
  return (
    <section id="demo" className="py-24 px-4 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-5xl">
        <div className="text-center mb-12">
          <h2 className="text-3xl sm:text-4xl font-bold text-foreground mb-4">
            See Sage Pontus in Action
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            질문 플로우 기반 AI가 어떻게 전략을 실행으로 전환하는지 확인하세요
          </p>
        </div>

        <div className="relative aspect-video rounded-2xl overflow-hidden bg-card border border-border shadow-2xl">
          <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-secondary/5" />
          
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <div className="relative mb-6">
              <div className="absolute inset-0 bg-primary/20 rounded-full blur-xl animate-pulse" />
              <Button
                size="lg"
                className="relative w-20 h-20 rounded-full bg-primary hover:bg-primary/90 text-primary-foreground shadow-lg"
              >
                <Play className="w-8 h-8 ml-1" />
              </Button>
            </div>
            
            <p className="text-muted-foreground text-sm">
              Click to watch the product demo
            </p>
          </div>

          <div className="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-background/80 to-transparent">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <span className="text-primary font-bold text-sm">SP</span>
                </div>
                <div>
                  <p className="font-medium text-foreground text-sm">Sage Pontus Demo</p>
                  <p className="text-xs text-muted-foreground">3:45</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                <span className="text-xs text-muted-foreground">HD Quality</span>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-12 grid sm:grid-cols-3 gap-6 text-center">
          {[
            { step: "01", title: "질문 입력", description: "비즈니스 목표와 컨텍스트를 자연어로 입력" },
            { step: "02", title: "AI 분석", description: "플로우 기반으로 전략적 인사이트 도출" },
            { step: "03", title: "실행 결과물", description: "즉시 활용 가능한 액션 아이템 생성" },
          ].map((item, index) => (
            <div key={index} className="p-6">
              <div className="w-12 h-12 rounded-full bg-secondary/10 flex items-center justify-center mx-auto mb-4">
                <span className="text-secondary font-bold">{item.step}</span>
              </div>
              <h3 className="font-semibold text-foreground mb-2">{item.title}</h3>
              <p className="text-sm text-muted-foreground">{item.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
