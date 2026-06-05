"use client"

import { useState, useCallback } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { CheckCircle2, Loader2 } from "lucide-react"

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

const INDUSTRIES = [
  { value: "physical_therapy", label: "물리치료 / 재활치료", enabled: true },
  { value: "sports_medicine", label: "스포츠의학", enabled: false },
  { value: "orthopedics", label: "정형외과", enabled: false },
  { value: "healthcare_general", label: "헬스케어 일반", enabled: false },
  { value: "other", label: "기타", enabled: false },
]

const schema = z.object({
  email: z.string().email("올바른 이메일 형식을 입력해주세요."),
  industry: z.string().min(1, "업종을 선택해주세요."),
})

type FormData = z.infer<typeof schema>

interface SignupModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function SignupModal({ open, onOpenChange }: SignupModalProps) {
  const [emailStatus, setEmailStatus] = useState<"idle" | "checking" | "available" | "taken">("idle")
  const [submitState, setSubmitState] = useState<"idle" | "loading" | "success">("idle")

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    setError,
    formState: { errors },
    reset,
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  const handleOpenChange = (next: boolean) => {
    if (!next) {
      reset()
      setEmailStatus("idle")
      setSubmitState("idle")
    }
    onOpenChange(next)
  }

  const checkEmail = useCallback(async (email: string) => {
    if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return
    setEmailStatus("checking")
    try {
      const res = await fetch(`/api/check-email/?email=${encodeURIComponent(email)}`)
      const data = await res.json()
      setEmailStatus(data.available ? "available" : "taken")
    } catch {
      setEmailStatus("idle")
    }
  }, [])

  const onSubmit = async (data: FormData) => {
    if (emailStatus === "taken") {
      setError("email", { message: "이미 등록된 이메일입니다." })
      return
    }
    setSubmitState("loading")
    try {
      const res = await fetch("/api/signup/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      })
      const result = await res.json()
      if (res.status === 201) {
        setSubmitState("success")
      } else if (res.status === 409) {
        setError("email", { message: "이미 등록된 이메일입니다." })
        setSubmitState("idle")
      } else {
        setError("email", { message: result.error || "오류가 발생했습니다. 다시 시도해주세요." })
        setSubmitState("idle")
      }
    } catch {
      setError("email", { message: "네트워크 오류가 발생했습니다." })
      setSubmitState("idle")
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        {submitState === "success" ? (
          <div className="flex flex-col items-center gap-4 py-8 text-center">
            <CheckCircle2 className="h-14 w-14 text-primary" />
            <DialogTitle className="text-xl font-semibold">신청이 완료되었습니다!</DialogTitle>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Early Access 신청을 받았습니다.<br />
              지금 바로 계정을 만들고 시작해 보세요.
            </p>
            <a
              href={`${process.env.NEXT_PUBLIC_PT_APP_URL ?? ""}/pt/signup/`}
              className="mt-2 w-full inline-flex items-center justify-center rounded-md bg-red-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-red-700 transition-colors"
            >
              계정 만들기 →
            </a>
            <Button variant="ghost" size="sm" onClick={() => handleOpenChange(false)}>
              나중에 하기
            </Button>
          </div>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>Early Access 신청</DialogTitle>
              <DialogDescription>
                이메일과 업종을 입력하시면 순서대로 안내 드립니다.
              </DialogDescription>
            </DialogHeader>

            <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-5 mt-2">
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="email">이메일</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="your@email.com"
                  {...register("email", {
                    onBlur: (e) => checkEmail(e.target.value),
                  })}
                  className={
                    emailStatus === "taken" || errors.email
                      ? "border-destructive focus-visible:ring-destructive"
                      : emailStatus === "available"
                      ? "border-green-500 focus-visible:ring-green-500"
                      : ""
                  }
                />
                {errors.email && (
                  <p className="text-xs text-destructive">{errors.email.message}</p>
                )}
                {emailStatus === "checking" && (
                  <p className="text-xs text-muted-foreground flex items-center gap-1">
                    <Loader2 className="h-3 w-3 animate-spin" /> 확인 중...
                  </p>
                )}
                {emailStatus === "available" && !errors.email && (
                  <p className="text-xs text-green-600">사용 가능한 이메일입니다.</p>
                )}
                {emailStatus === "taken" && !errors.email && (
                  <p className="text-xs text-destructive">이미 등록된 이메일입니다.</p>
                )}
              </div>

              <div className="flex flex-col gap-1.5">
                <Label htmlFor="industry">업종</Label>
                <Select onValueChange={(val) => setValue("industry", val, { shouldValidate: true })}>
                  <SelectTrigger id="industry" className={errors.industry ? "border-destructive" : ""}>
                    <SelectValue placeholder="업종을 선택해주세요" />
                  </SelectTrigger>
                  <SelectContent>
                    {INDUSTRIES.filter((i) => i.enabled).map((industry) => (
                      <SelectItem key={industry.value} value={industry.value}>
                        {industry.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {errors.industry && (
                  <p className="text-xs text-destructive">{errors.industry.message}</p>
                )}
              </div>

              <Button
                type="submit"
                className="w-full bg-primary hover:bg-primary/90 text-primary-foreground"
                disabled={submitState === "loading" || emailStatus === "taken"}
              >
                {submitState === "loading" ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" /> 신청 중...
                  </span>
                ) : (
                  "Early Access 신청하기"
                )}
              </Button>
            </form>
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}
