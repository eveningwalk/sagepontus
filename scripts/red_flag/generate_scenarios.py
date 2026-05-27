"""
PT Red Flag 합성 시나리오 생성기
Gemini API로 현실적인 PT SOAP 텍스트 생성 → validate_scenarios.py 형식으로 저장

사용법:
    python scripts/red_flag/generate_scenarios.py
    python scripts/red_flag/generate_scenarios.py --count 50 --out data/soap_samples/synthetic_scenarios.json
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()
ROOT = Path(__file__).resolve().parents[2]

# ── 생성 요청 템플릿 ──────────────────────────────────────────────────────────
# (condition, alarm_level, id_prefix, description_hint, count)
GENERATION_PLAN = [
    # RED cases
    ("cauda_equina",  "RED",    "CES",  "Cauda Equina Syndrome — 방광/장 기능 이상, 안장 감각 소실, 양측 하지 무력", 5),
    ("fracture",      "RED",    "FX",   "Spinal/Hip Fracture — 고령 낙상, 골다공증, 타진 압통, 체중부하 통증",    5),
    ("malignancy",    "RED",    "CA",   "Malignancy — 설명 불가 체중감소, 야간통, 암 기왕력, 비기계적 통증",      5),
    ("infection",     "RED",    "INF",  "Spinal Infection — 발열, 최근 수술/면역저하, 안정시 통증 악화",          4),
    ("vascular",      "RED",    "AAA",  "Vascular — 복부 박동성 통증, 하지 창백/냉감, 안정시 통증",              3),
    # YELLOW cases
    (None,            "YELLOW", "YEL",  "Yellow Flag — 우울/불안, 수면장애, 통증 과장, 회피 행동, 직업 스트레스", 8),
    # NONE cases (true negative — Red Flag 없는 일반 PT 케이스)
    (None,            "NONE",   "NONE", "일반 PT 케이스 — LBP, 어깨 통증, 무릎, 발목, 경부통. Red Flag 없음",    10),
]

SYSTEM_PROMPT = """\
You are a clinical documentation expert for physical therapy.
Generate realistic, concise PT SOAP note snippets (2-5 sentences each) for training a Red Flag detection algorithm.

Rules:
- Write in English clinical shorthand (abbreviations OK: pt, c/o, PMH, ROM, MMT, etc.)
- Each snippet must be unique — vary age, sex, body region, symptom combination
- For RED cases: include 1-3 clear Red Flag indicators matching the condition
- For YELLOW cases: psychosocial flags only, no physical Red Flags
- For NONE cases: routine PT presentation, explicitly deny Red Flags where natural
- Do NOT include diagnoses — write as objective/subjective observations only
- Keep each snippet under 100 words
"""


def _call_gemini(prompt: str) -> str:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(".env에 GEMINI_API_KEY가 없습니다.")
    url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
    resp = requests.post(
        url,
        json={
            "model": "gemini-2.5-flash",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": prompt},
            ],
            "temperature": 0.9,
            "max_tokens": 3000,
        },
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def generate_batch(condition: str | None, alarm: str, id_prefix: str,
                   hint: str, count: int, id_offset: int) -> list[dict]:
    prompt = f"""
Generate exactly {count} PT SOAP note snippets for the following scenario type:
- Alarm level: {alarm}
- Condition: {condition or 'N/A (psychosocial or routine)'}
- Clinical focus: {hint}

Return a JSON array only, no other text:
[
  {{
    "id": "{id_prefix}_XX",
    "description": "brief Korean description (20자 이내)",
    "soap_text": "English PT SOAP snippet",
    "expected_alarm": "{alarm}",
    "expected_condition": "{condition or 'none'}"
  }},
  ...
]

Number the IDs sequentially starting from {id_prefix}_{id_offset+1:02d}.
"""

    raw = _call_gemini(prompt)

    # JSON 블록 추출 (마크다운 코드펜스 제거 후)
    import re
    raw = re.sub(r"```(?:json)?\s*", "", raw).strip()
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    if not m:
        print(f"  [warn] JSON 파싱 실패, raw:\n{raw[:200]}", file=sys.stderr)
        return []
    return json.loads(m.group(0))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/soap_samples/synthetic_scenarios.json")
    args = parser.parse_args()

    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)

    all_scenarios = []
    id_counters: dict[str, int] = {}

    for condition, alarm, prefix, hint, count in GENERATION_PLAN:
        offset = id_counters.get(prefix, 0)
        print(f"생성 중: {prefix} ({alarm}) {count}건...")
        try:
            batch = generate_batch(condition, alarm, prefix, hint, count, offset)
            all_scenarios.extend(batch)
            id_counters[prefix] = offset + len(batch)
            print(f"  → {len(batch)}건 완료")
        except Exception as e:
            print(f"  [error] {e}", file=sys.stderr)
        time.sleep(1)

    out_path.write_text(json.dumps(all_scenarios, ensure_ascii=False, indent=2))
    print(f"\n총 {len(all_scenarios)}건 → {out_path}")

    # 분포 요약
    from collections import Counter
    dist = Counter(s["expected_alarm"] for s in all_scenarios)
    for level, cnt in sorted(dist.items()):
        print(f"  {level}: {cnt}건")


if __name__ == "__main__":
    main()
