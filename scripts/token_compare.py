#!/usr/bin/env python3
"""
A vs B 프롬프트 토큰 비교 스크립트

[비교 구조]
  A (기존 방식):
    매 세션마다 PT가 배경 + 환자정보 + 요청을 통째로 입력
    → 세션마다 전체 토큰 소모 + 작성 시간 소요

  B (Sage Pontus):
    b_system = 프로필 기반 정적 프롬프트 (1회 생성, 저장해두고 붙여넣기)
    b_task   = 케이스별 짧은 환자정보 + 요청 (매 세션 추가)
    → 세션마다 b_system + b_task 토큰만 소모, b_task만 새로 작성

사용법:
  python scripts/token_compare.py                        # 대화형 입력
  python scripts/token_compare.py cases.json             # JSON 파일 입력
  python scripts/token_compare.py --sample               # 샘플 케이스 실행

JSON 파일 형식 (generate_b_prompt.py 출력과 동일):
  [
    {
      "case":     "케이스 이름",
      "prompt_a": "PT가 매 세션 통째로 입력하는 내용",
      "b_system": "Sage Pontus가 생성한 정적 프로필 프롬프트",
      "b_task":   "케이스별 짧은 환자정보 + 요청"
    }
  ]
"""

import sys
import json
import re
from pathlib import Path
from datetime import datetime


# ── 모델 단가 테이블 ($/1M input tokens, 2025년 기준) ────────────────────
MODEL_PRICING = {
    "Gemini 2.5 Flash":  {"input": 0.15,  "tier": "저가"},
    "Claude Haiku 4.5":  {"input": 0.80,  "tier": "저가"},
    "GPT-4o mini":       {"input": 0.15,  "tier": "저가"},
    "Claude Sonnet 4.5": {"input": 3.00,  "tier": "중가"},
    "GPT-4o":            {"input": 2.50,  "tier": "고가"},
}

MONTHLY_SESSIONS = 200  # 물리치료사 1인 기준 월 세션 수


# ── 토큰 카운터 ────────────────────────────────────────────────────────────
def count_tokens(text: str) -> int:
    """
    한국어/영어 혼합 텍스트 토큰 수 근사.
      한글 음절 ~1.5 tokens / ASCII 4자 ~1 token
    """
    korean = len(re.findall(r'[가-힣]', text))
    others = len(re.sub(r'[가-힣\s]', '', text))
    spaces = len(re.findall(r'\s+', text))
    return int(korean * 1.5 + others / 4 + spaces * 0.3)


def monthly_cost(tokens: int, price_per_1m: float) -> float:
    return tokens * price_per_1m / 1_000_000 * MONTHLY_SESSIONS


# ── 출력 유틸 ──────────────────────────────────────────────────────────────
def hr(char="─", width=66):
    print(char * width)

def section(title):
    print()
    hr("═")
    print(f"  {title}")
    hr("═")


# ── 케이스 분석 ────────────────────────────────────────────────────────────
def analyze_case(case: dict) -> dict:
    prompt_a = case.get("prompt_a", "")
    b_system = case.get("b_system", "")
    b_task   = case.get("b_task", "")

    tok_a        = count_tokens(prompt_a)
    tok_b_system = count_tokens(b_system)
    tok_b_task   = count_tokens(b_task)
    tok_b_total  = tok_b_system + tok_b_task

    reduction = (tok_a - tok_b_total) / tok_a * 100 if tok_a else 0

    # 매 세션 PT가 새로 작성하는 분량 비교
    # A: 전체를 새로 작성, B: b_task만 새로 작성 (b_system은 저장해서 붙여넣기)
    writing_reduction = (tok_a - tok_b_task) / tok_a * 100 if tok_a else 0

    return {
        "case":             case.get("case", "케이스"),
        "tok_a":            tok_a,
        "tok_b_system":     tok_b_system,
        "tok_b_task":       tok_b_task,
        "tok_b_total":      tok_b_total,
        "reduction":        reduction,
        "writing_reduction": writing_reduction,
        "len_a":            len(prompt_a),
        "len_b_system":     len(b_system),
        "len_b_task":       len(b_task),
    }


def print_case_result(r: dict):
    section(f"케이스: {r['case']}")

    # 토큰 브레이크다운
    print(f"  {'':35} {'A (기존)':>10} {'B (Sage)':>10}")
    hr()
    print(f"  {'[A] 전체 입력 (배경+환자+요청)':35} {r['tok_a']:>10,}")
    print()
    print(f"  {'[B] b_system  (정적, 저장해두고 재사용)':35} {'':>10} {r['tok_b_system']:>10,}")
    print(f"  {'[B] b_task    (케이스별 추가, 매 세션)':35} {'':>10} {r['tok_b_task']:>10,}")
    print(f"  {'[B] 합계 (b_system + b_task)':35} {'':>10} {r['tok_b_total']:>10,}")
    hr()
    print(f"  {'AI 입력 토큰 절감율':35} {'':>10} {r['reduction']:>9.1f}%")
    print(f"  {'매 세션 직접 작성 분량 절감율':35} {'':>10} {r['writing_reduction']:>9.1f}%")
    hr()

    # 모델별 월간 비용
    print(f"\n  [모델별 월간 비용]  (월 {MONTHLY_SESSIONS}세션 기준)")
    print(f"  {'모델':20} {'등급':6} {'A 월비용':>10} {'B 월비용':>10} {'절감액':>10} {'절감율':>8}")
    hr()
    for model, p in MODEL_PRICING.items():
        ca = monthly_cost(r['tok_a'],       p['input'])
        cb = monthly_cost(r['tok_b_total'], p['input'])
        saved = ca - cb
        pct   = saved / ca * 100 if ca else 0
        print(f"  {model:20} {p['tier']:6} ${ca:>8.4f}  ${cb:>8.4f}  ${saved:>8.4f}  {pct:>7.1f}%")
    hr()


def print_summary(results: list):
    section("전체 요약")

    avg_a          = sum(r['tok_a']        for r in results) / len(results)
    avg_b          = sum(r['tok_b_total']  for r in results) / len(results)
    avg_b_task     = sum(r['tok_b_task']   for r in results) / len(results)
    avg_reduction  = sum(r['reduction']    for r in results) / len(results)
    avg_writing    = sum(r['writing_reduction'] for r in results) / len(results)

    print(f"  분석 케이스 수:              {len(results)}개")
    print(f"  평균 A 토큰 (매 세션 전체):  {avg_a:.0f} tokens")
    print(f"  평균 B 토큰 (system+task):   {avg_b:.0f} tokens  (절감 {avg_reduction:.0f}%)")
    print(f"  평균 b_task (새로 작성분):   {avg_b_task:.0f} tokens  (A 대비 {avg_writing:.0f}% 절감)")
    hr()

    print("\n  [마케팅 문구 초안]")
    print(f"  → AI 입력 토큰: 기존 대비 평균 {avg_reduction:.0f}% 절감")
    print(f"  → 세션당 직접 작성 분량: 기존 대비 평균 {avg_writing:.0f}% 절감")
    print(f"  → b_system은 한 번 만들면 저장 후 붙여넣기 — 반복 설명 불필요")
    print()


# ── 샘플 케이스 (generate_b_prompt.py --sample 결과 기준) ────────────────
SAMPLE_CASES = [
    {
        "case": "뇌졸중 환자 SOAP 노트",
        "prompt_a": (
            "저는 재활병원에서 근무하는 물리치료사예요. "
            "주로 뇌졸중 편마비 환자를 담당해요. "
            "오늘 환자는 65세 남성이고, 3개월 전 좌측 MCA 뇌졸중 이후 "
            "우측 편마비가 왔어요. Berg Balance Scale 28점, 10MWT 0.4m/s예요. "
            "저는 보통 PNF 기반으로 접근하는데, 보험 청구 서류도 자주 써야 해서 "
            "ICD-10 코드도 잘 알고 있어야 해요. SOAP 형식으로 작성해줘요."
        ),
        "b_system": (
            "# 역할과 상황\n"
            "재활병원 신경과 병동 소속 물리치료사. 뇌졸중 후 편마비 성인(60~80대) 전담.\n\n"
            "# 목표\n"
            "SOAP 노트 작성, 보험 청구 서류(ICD-10) 대응, 보행 재활 프로토콜 설계.\n\n"
            "# 기대 응답 방식\n"
            "의료 기록 형식으로 간결하게. PNF·과제지향훈련 관점 반영. EBP 근거 한 줄 포함."
        ),
        "b_task": "65세 남성, MCA 뇌졸중 3개월, 우측 편마비. Berg 28, 10MWT 0.4m/s. SOAP 노트 작성.",
    },
    {
        "case": "ACL 재건술 후 HEP",
        "prompt_a": (
            "저는 스포츠 클리닉에서 일하는 물리치료사인데요, "
            "이번에 ACL 재건술을 받은 25세 남성 환자가 있어요. "
            "수술 후 6주가 됐고 현재 보조기 착용 중이에요. "
            "ROM은 신전 -5도, 굴곡 100도예요. MMT는 대퇴사두근 3+/5예요. "
            "아직 달리기는 안 되고 자전거 정도는 가능한 시기예요. "
            "환자가 20대 운동선수라서 복귀 목표가 있어요. "
            "홈 운동 프로그램을 만들어줄 수 있어요?"
        ),
        "b_system": (
            "# 역할과 상황\n"
            "재활병원 신경과 병동 소속 물리치료사. 뇌졸중 후 편마비 성인(60~80대) 전담.\n\n"
            "# 목표\n"
            "SOAP 노트 작성, 보험 청구 서류(ICD-10) 대응, 보행 재활 프로토콜 설계.\n\n"
            "# 기대 응답 방식\n"
            "의료 기록 형식으로 간결하게. PNF·과제지향훈련 관점 반영. EBP 근거 한 줄 포함."
        ),
        "b_task": "25세 남성, ACL 재건술 6주. 보조기 착용, ROM 신전 -5°/굴곡 100°, 대퇴사두근 MMT 3+. 6주차 HEP 작성.",
    },
]


# ── 대화형 입력 ────────────────────────────────────────────────────────────
def interactive_input() -> list:
    print("\nSage Pontus — A/B 프롬프트 토큰 비교")
    print("(입력 종료: 케이스 이름에서 빈 줄 Enter)\n")

    cases = []
    while True:
        name = input("케이스 이름 (빈 줄: 종료): ").strip()
        if not name:
            break

        def read_block(label):
            print(f"{label} (여러 줄, 빈 줄로 종료):")
            lines = []
            while True:
                line = input()
                if not line:
                    break
                lines.append(line)
            return "\n".join(lines)

        prompt_a = read_block("A 프롬프트 (PT 원본 전체)")
        b_system = read_block("b_system (Sage 생성 정적 프롬프트)")
        b_task   = read_block("b_task (케이스별 짧은 추가)")

        cases.append({"case": name, "prompt_a": prompt_a, "b_system": b_system, "b_task": b_task})

    return cases


# ── 결과 저장 ──────────────────────────────────────────────────────────────
def save_results(cases: list, results: list):
    out = {
        "generated_at":            datetime.now().isoformat(),
        "monthly_sessions_assumed": MONTHLY_SESSIONS,
        "cases": [{**c, "result": r} for c, r in zip(cases, results)],
    }
    path = Path(f"scripts/token_compare_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  결과 저장: {path}")


# ── 메인 ───────────────────────────────────────────────────────────────────
def main():
    args = sys.argv[1:]

    if "--sample" in args:
        cases = SAMPLE_CASES
        print("[샘플 케이스로 실행]")
    elif args and args[0].endswith(".json"):
        path = Path(args[0])
        if not path.exists():
            print(f"파일 없음: {args[0]}")
            sys.exit(1)
        cases = json.loads(path.read_text(encoding="utf-8"))
    else:
        cases = interactive_input()

    if not cases:
        print("케이스가 없습니다.")
        return

    results = []
    for case in cases:
        r = analyze_case(case)
        print_case_result(r)
        results.append(r)

    if len(results) > 1:
        print_summary(results)

    save_results(cases, results)


if __name__ == "__main__":
    main()
