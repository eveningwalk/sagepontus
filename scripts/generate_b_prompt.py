#!/usr/bin/env python3
"""
Sage Pontus B 프롬프트 생성기

[구조]
  b_system  = PT 프로필 기반 정적 컨텍스트 (1회 생성, 매 세션 재사용)
  b_task    = 케이스별 짧은 환자 정보 + 요청 (매 세션 새로 추가)

  A (기존)  = 배경 + 환자정보 + 요청  → 매 세션 통째로 재입력
  B (Sage)  = b_system (저장) + b_task (짧게 추가)

사용법:
  python scripts/generate_b_prompt.py              # 샘플 PT 데이터로 실행
  python scripts/generate_b_prompt.py pt_data.json # PT 데이터 JSON 입력

PT 데이터 JSON 형식:
  {
    "profile": {
      "근무환경": "재활병원 신경과 병동",
      "전문분야": "뇌졸중 편마비, 신경계 재활",
      "주환자군": "뇌졸중 후 편마비 성인, 60~80대",
      "치료접근법": "PNF, 과제지향훈련, 보행 재활",
      "주사용서류": "SOAP 노트, 보험 청구 서류",
      "평가도구": "Berg Balance Scale, FIM, 10MWT, MMT"
    },
    "cases": [
      {
        "case": "케이스 이름",
        "prompt_a": "PT가 매 세션 실제로 입력하는 전체 내용 (배경+환자+요청)",
        "b_task": "케이스별 짧은 환자정보 + 요청 (PT가 매 세션 추가하는 부분)"
      }
    ]
  }

출력: scripts/cases_with_b_prompt.json  → token_compare.py 에 바로 사용 가능
"""

import json
import os
import sys
from pathlib import Path

import requests
from jinja2 import Environment, FileSystemLoader

# ── 환경 변수 로드 ────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent

def _load_env(env_path: Path):
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip())

_load_env(ROOT / ".env")

PROMPTS_DIR = ROOT / "questionnaire" / "prompts" / "versions" / "v2"

# ── Jinja2 템플릿 ──────────────────────────────────────────────────────────
_jinja = Environment(
    loader=FileSystemLoader(str(PROMPTS_DIR)),
    autoescape=False,
    trim_blocks=True,
    lstrip_blocks=True,
)
_system_tmpl = _jinja.get_template("prompt_builder_system.jinja")
_user_tmpl   = _jinja.get_template("prompt_builder_user.jinja")


# ── Gemini 호출 ────────────────────────────────────────────────────────────
def _call_gemini(system_prompt: str, user_prompt: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(".env에 GEMINI_API_KEY가 없습니다.")

    url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    payload = {
        "model": "gemini-2.5-flash-lite",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        "max_tokens": 2048,
        "temperature": 0.4,
    }
    resp = requests.post(
        url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


# ── Q&A 포맷 ──────────────────────────────────────────────────────────────
def _format_qa_pairs(qa_list: list[dict]) -> str:
    parts = []
    for i, item in enumerate(qa_list, 1):
        parts.append(
            f"[{i}] 분류: {item.get('category', '프로필')}\n"
            f"질문: {item['q']}\n"
            f"답변: {item['a']}"
        )
    return "\n\n".join(parts)


# ── 프로필 → Q&A 변환 (케이스 컨텍스트 제외) ─────────────────────────────
PROFILE_QUESTIONS = [
    ("근무환경",    "어떤 환경에서 근무하시나요?"),
    ("전문분야",    "전문 분야 또는 주로 다루는 질환은 무엇인가요?"),
    ("주환자군",    "주로 담당하는 환자군(연령, 진단)은 어떻게 되나요?"),
    ("치료접근법",  "선호하는 치료 접근법이나 프레임워크가 있나요?"),
    ("평가도구",    "자주 사용하는 평가 도구나 측정 방법은 무엇인가요?"),
    ("주사용서류",  "주로 작성하는 문서 유형은 무엇인가요?"),
]

def profile_to_qa(profile: dict) -> list[dict]:
    return [
        {"category": "물리치료사 프로필", "q": q, "a": profile[key]}
        for key, q in PROFILE_QUESTIONS
        if profile.get(key)
    ]


# ── b_system 생성 (프로필만, 케이스 무관) ────────────────────────────────
def generate_b_system(profile: dict) -> str:
    qa = profile_to_qa(profile)
    qa_text = _format_qa_pairs(qa)

    system_prompt = _system_tmpl.render()
    user_prompt   = _user_tmpl.render(
        qa_pairs=qa_text,
        domain_focus="physical_therapy",
    )

    print("  → b_system 생성 중 (Gemini)...", end=" ", flush=True)
    result = _call_gemini(system_prompt, user_prompt)
    print("완료")
    return result


# ── 샘플 데이터 ───────────────────────────────────────────────────────────
SAMPLE_PT_DATA = {
    "profile": {
        "근무환경":    "재활병원 신경과 병동",
        "전문분야":    "뇌졸중 편마비, 신경계 재활",
        "주환자군":    "뇌졸중 후 편마비 성인, 주로 60~80대",
        "치료접근법":  "PNF, 과제지향훈련(Task-Oriented Training), 보행 재활",
        "평가도구":    "Berg Balance Scale, FIM, 10MWT, MMT",
        "주사용서류":  "SOAP 노트, 보험 청구 서류, 재활 경과 기록",
    },
    "cases": [
        {
            "case": "뇌졸중 환자 SOAP 노트",
            # PT가 매 세션 통째로 입력하는 내용 (배경 + 환자 + 요청)
            "prompt_a": (
                "저는 재활병원에서 근무하는 물리치료사예요. "
                "주로 뇌졸중 편마비 환자를 담당해요. "
                "오늘 환자는 65세 남성이고, 3개월 전 좌측 MCA 뇌졸중 이후 "
                "우측 편마비가 왔어요. Berg Balance Scale 28점, 10MWT 0.4m/s예요. "
                "저는 보통 PNF 기반으로 접근하는데, 보험 청구 서류도 자주 써야 해서 "
                "ICD-10 코드도 잘 알고 있어야 해요. SOAP 형식으로 작성해줘요."
            ),
            # PT가 매 세션 추가하는 짧은 내용 (환자 정보 + 요청만)
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
            "b_task": "25세 남성, ACL 재건술 6주. 보조기 착용, ROM 신전 -5°/굴곡 100°, 대퇴사두근 MMT 3+. 6주차 HEP 작성.",
        },
    ],
}


# ── 메인 ───────────────────────────────────────────────────────────────────
def main():
    args = sys.argv[1:]

    if args and not args[0].startswith("--"):
        data = json.loads(Path(args[0]).read_text(encoding="utf-8"))
    else:
        data = SAMPLE_PT_DATA
        print("[샘플 PT 데이터로 실행]\n")

    profile = data["profile"]
    cases   = data["cases"]

    # b_system은 프로필 기준 1회만 생성
    print("[프로필 기반 b_system 생성]")
    b_system = generate_b_system(profile)
    print(f"\n── b_system (재사용 고정 프롬프트) ──\n{b_system}\n")

    output_cases = []
    for i, case in enumerate(cases, 1):
        print(f"[{i}/{len(cases)}] {case['case']}")
        b_task = case.get("b_task", "")
        print(f"  b_task: {b_task}\n")

        output_cases.append({
            "case":     case["case"],
            "prompt_a": case["prompt_a"],
            "b_system": b_system,
            "b_task":   b_task,
        })

    out_path = ROOT / "scripts" / "cases_with_b_prompt.json"
    out_path.write_text(
        json.dumps(output_cases, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"저장 완료: {out_path}")
    print(f"\n토큰 비교 실행:")
    print(f"  python scripts/token_compare.py scripts/cases_with_b_prompt.json")


if __name__ == "__main__":
    main()
