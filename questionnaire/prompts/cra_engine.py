"""
CRA (Context Retention Algorithm) Engine v2

처리 흐름:
  1. KB 로드: 도메인 + common KB를 합산
  2. 이전 세션 CRAAsset 로드 → Call 1 프롬프트에 previous_context 주입
  3. 규칙 기반 1차 패스: synonym 매칭 (빠름, 비용 없음)
  4. AI 2차 패스: 1차에서 못 잡은 토큰 or 신뢰도 낮은 항목 보완 (선택적)
  5. AMBIGUITY_HALT: 신뢰도 0.7 미만 토큰 있으면 중단 및 질문 반환
  6. Call 2 결과를 CRAAsset에 저장 → 다음 세션에서 재사용

외부 인터페이스:
  process_cra(raw_input, domain=None, use_ai=False) -> dict
  run_cra_pipeline(raw_input, domain, use_ai, user, braintree) -> dict
  enrich_qa_text(qa_text, domain=None) -> str
  load_kb(domain) -> dict
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_KB_DIR = Path(__file__).resolve().parent / "kb"
_VERSIONS_DIR = Path(__file__).resolve().parent / "versions" / "v2"
_CRA_CALL1_TEMPLATE = _VERSIONS_DIR / "cra_call1.jinja"
_CRA_CALL2_TEMPLATE = _VERSIONS_DIR / "cra_call2.jinja"
_CRA_CALL3_TEMPLATE = _VERSIONS_DIR / "cra_call3.jinja"
_AMBIGUITY_THRESHOLD = 0.70


# ---------------------------------------------------------------------------
# KB 로딩
# ---------------------------------------------------------------------------

def load_kb(domain: str | None = None) -> dict:
    """
    common KB + 도메인 KB를 합산해서 반환.
    domain=None 이면 common만 반환.
    """
    kb: dict = {}

    common_path = _KB_DIR / "common.json"
    if common_path.exists():
        with open(common_path, encoding="utf-8") as f:
            kb.update(json.load(f))

    if domain:
        domain_path = _KB_DIR / f"{domain}.json"
        if domain_path.exists():
            with open(domain_path, encoding="utf-8") as f:
                kb.update(json.load(f))
        else:
            logger.debug("KB 파일 없음: %s", domain_path)

    return kb


# ---------------------------------------------------------------------------
# 규칙 기반 1차 매핑
# ---------------------------------------------------------------------------

def _rule_based_match(text: str, kb: dict) -> list[dict]:
    """KB의 label + synonyms로 문자열 매칭."""
    hits: list[dict] = []
    seen_kb_ids: set[str] = set()

    # 긴 synonym 먼저 처리 (부분 중복 방지)
    entries: list[tuple[str, str, dict]] = []
    for kb_id, entry in kb.items():
        for syn in [entry["label"]] + entry.get("synonyms", []):
            entries.append((syn, kb_id, entry))
    entries.sort(key=lambda x: len(x[0]), reverse=True)

    for synonym, kb_id, entry in entries:
        if kb_id in seen_kb_ids:
            continue
        if synonym in text:
            seen_kb_ids.add(kb_id)
            hits.append({
                "raw": synonym,
                "kb_id": kb_id,
                "label": entry["label"],
                "confidence": 1.0 if synonym == entry["label"] else 0.88,
                "depth": entry["depth"],
                "category": entry["category"],
            })

    return sorted(hits, key=lambda h: h["depth"], reverse=True)


# ---------------------------------------------------------------------------
# AI 기반 2차 패스 (선택적)
# ---------------------------------------------------------------------------

def _slim_kb(kb: dict) -> str:
    """
    AI 프롬프트용 경량 KB — label + synonyms 리스트만 포함.
    depth/category 제거로 토큰 절감.
    """
    slim = {
        kb_id: [entry["label"]] + entry.get("synonyms", [])
        for kb_id, entry in kb.items()
    }
    return json.dumps(slim, ensure_ascii=False, separators=(",", ":"))


def _extract_json(raw: str) -> str:
    """
    AI 응답에서 JSON 블록 추출.
    코드펜스 제거 후 첫 번째 { ... } 범위를 반환한다.
    응답이 잘린 경우에도 최대한 복원을 시도한다.
    """
    text = raw.strip()
    # 코드펜스 제거
    if "```" in text:
        parts = text.split("```")
        for part in parts[1:]:
            candidate = re.sub(r"^json\s*", "", part).strip()
            if candidate.startswith("{"):
                text = candidate
                break
    # 첫 번째 { 부터 추출
    start = text.find("{")
    if start == -1:
        return text
    text = text[start:]
    # 후행 쉼표 제거 (LLM이 생성하는 흔한 비표준 패턴)
    text = re.sub(r",\s*([}\]])", r"\1", text)
    # 닫히지 않은 JSON 복원 시도
    try:
        json.loads(text)
        return text
    except json.JSONDecodeError:
        pass
    # 열린 괄호 수를 세어 강제 닫기
    depth_brace = depth_bracket = 0
    in_string = False
    escape = False
    last_good = 0
    for i, ch in enumerate(text):
        if escape:
            escape = False
            continue
        if ch == "\\" and in_string:
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth_brace += 1
        elif ch == "}":
            depth_brace -= 1
        elif ch == "[":
            depth_bracket += 1
        elif ch == "]":
            depth_bracket -= 1
        if depth_brace == 0 and depth_bracket == 0 and i > 0:
            last_good = i + 1
            break
    else:
        # 잘린 경우: 문자열 내부에서 잘렸으면 먼저 닫고, 그 뒤 괄호를 닫는다
        close = ""
        if in_string:
            close += '"'
        close += "]" * depth_bracket + "}" * depth_brace
        return text + close
    return text[:last_good]


def _ai_tokenize(raw_input: str, kb: dict, previous_context: str | None = None) -> dict | None:
    """
    cra_call1.jinja 프롬프트로 AI 호출 → 토크나이제이션 결과 반환.
    실패 시 None 반환 (규칙 기반 결과로 폴백).
    """
    if not _CRA_CALL1_TEMPLATE.exists():
        logger.warning("CRA Call1 템플릿 없음: %s", _CRA_CALL1_TEMPLATE)
        return None

    try:
        from jinja2 import Template
        tmpl = Template(_CRA_CALL1_TEMPLATE.read_text(encoding="utf-8"))
        prompt = tmpl.render(
            domain_kb=_slim_kb(kb),        # 경량 KB (label+synonyms만)
            raw_input=raw_input,
            previous_context=previous_context,
        )
    except Exception as e:
        logger.warning("CRA 프롬프트 렌더 실패: %s", e)
        return None

    try:
        from questionnaire.prompts.service import _chat_generate
        raw_response = _chat_generate()(
            "gemini-2.0-flash",
            prompt,
            {"max_tokens": 3000, "temperature": 0.1},
        )
    except Exception as e:
        logger.warning("CRA AI 호출 실패: %s", e)
        return None

    try:
        return json.loads(_extract_json(raw_response))
    except json.JSONDecodeError as e:
        logger.warning("CRA AI 응답 JSON 파싱 실패: %s\n원문: %.200s", e, raw_response)
        return None


# ---------------------------------------------------------------------------
# 환자 메타 추출 (범용 컨텍스트 힌트)
# ---------------------------------------------------------------------------

def _extract_meta(text: str) -> dict:
    age_m = re.search(r"(\d+)대", text)
    gender_m = re.search(r"(남자|여자|남성|여성)", text)
    return {
        "age_group": age_m.group(0) if age_m else None,
        "gender": (
            "M" if gender_m and "남" in gender_m.group(0)
            else "F" if gender_m and "여" in gender_m.group(0)
            else None
        ),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def process_cra(
    raw_input: str,
    domain: str | None = None,
    use_ai: bool = False,
    previous_context: str | None = None,
) -> dict[str, Any]:
    """
    CRA 파이프라인 실행.

    Args:
        raw_input: 사용자 원문 텍스트
        domain:    도메인 이름 (startup, marketing 등). None이면 common만 사용.
        use_ai:    True면 AI 2차 패스 실행 (API 비용 발생)

    Returns:
        status == "OK"             → 정상 처리 결과
        status == "AMBIGUITY_HALT" → 신뢰도 미달, question 포함
    """
    kb = load_kb(domain)

    if use_ai:
        ai_result = _ai_tokenize(raw_input, kb, previous_context=previous_context)
        if ai_result:
            # AI 결과를 그대로 사용 (AMBIGUITY_HALT 포함)
            ai_result["source"] = "ai"
            ai_result["meta"] = _extract_meta(raw_input)
            return ai_result

    # 규칙 기반 처리
    hits = _rule_based_match(raw_input, kb)
    low_confidence = [h for h in hits if h["confidence"] < _AMBIGUITY_THRESHOLD]

    if low_confidence:
        return {
            "status": "AMBIGUITY_HALT",
            "question": (
                f"다음 표현의 의미가 불명확합니다: "
                f"{[h['raw'] for h in low_confidence]}. "
                "정확한 맥락을 보충해 주세요."
            ),
            "source": "rule",
        }

    return {
        "status": "OK",
        "source": "rule",
        "meta": _extract_meta(raw_input),
        "domain_hits": hits,
        "token_count": len(hits),
    }


def _rule_based_call2(call1_result: dict) -> dict:
    """
    AI 없이 Call 1 결과를 Steps 2–4로 처리하는 규칙 기반 폴백.
    """
    hits = call1_result.get("domain_hits", [])
    raw_tokens = call1_result.get("raw_tokens", [])

    # Step 2: Semantic Mapping
    refined: list[dict] = []
    hit_raws = {h["raw"] for h in hits}
    for h in hits:
        refined.append({
            "original": h["raw"],
            "standard": h["label"],
            "kb_id": h["kb_id"],
            "depth_score": h["depth"],
            "category": h["category"],
        })
    # 매핑 안 된 raw_tokens
    for tok in raw_tokens:
        if tok not in hit_raws:
            refined.append({
                "original": tok,
                "standard": f"[AMBIGUOUS:{tok}]",
                "kb_id": None,
                "depth_score": 0.3,
                "category": "unknown",
            })

    refined.sort(key=lambda t: t["depth_score"], reverse=True)

    # Step 3: depth_summary
    scores = [t["depth_score"] for t in refined if t["depth_score"] > 0]
    peak = refined[0] if refined else {}
    avg = round(sum(scores) / len(scores), 3) if scores else 0.0

    # Step 4: Context Orchestration
    def _collect(categories):
        return [t["standard"] for t in refined if t["category"] in categories
                and not t["standard"].startswith("[AMBIGUOUS")]

    context = {
        "primary_focus":    ", ".join(_collect({"core_concept"})) or "미확인",
        "inferred_goal":    _collect({"objective", "execution"}),
        "constraint_cluster": _collect({"constraint", "resource"}),
        "temporal_pattern": "unknown",
        "expert_state": (
            "solution_design"    if _collect({"execution"})
            else "problem_scoping" if _collect({"core_concept", "problem"})
            else "unknown"
        ),
    }

    return {
        "refined_tokens": refined,
        "noise_removed": [],
        "context": context,
        "depth_summary": {
            "peak_token": peak.get("standard", ""),
            "peak_score": peak.get("depth_score", 0.0),
            "avg_score": avg,
        },
        "source": "rule",
    }


def _ai_call2(call1_result: dict) -> dict | None:
    """cra_call2.jinja 프롬프트로 AI 호출 → Steps 2–4 결과 반환."""
    if not _CRA_CALL2_TEMPLATE.exists():
        logger.warning("CRA Call2 템플릿 없음: %s", _CRA_CALL2_TEMPLATE)
        return None

    try:
        from jinja2 import Template
        tmpl = Template(_CRA_CALL2_TEMPLATE.read_text(encoding="utf-8"))
        prompt = tmpl.render(
            call1_result=json.dumps(call1_result, ensure_ascii=False, indent=2)
        )
    except Exception as e:
        logger.warning("CRA Call2 프롬프트 렌더 실패: %s", e)
        return None

    try:
        from questionnaire.prompts.service import _chat_generate
        raw_response = _chat_generate()(
            "gemini-2.0-flash",
            prompt,
            {"max_tokens": 2500, "temperature": 0.1},
        )
    except Exception as e:
        logger.warning("CRA Call2 AI 호출 실패: %s", e)
        return None

    try:
        result = json.loads(_extract_json(raw_response))
        result["source"] = "ai"
        return result
    except json.JSONDecodeError as e:
        logger.warning("CRA Call2 JSON 파싱 실패: %s\n원문: %.200s", e, raw_response)
        return None


def run_cra_pipeline(
    raw_input: str,
    domain: str | None = None,
    use_ai: bool = False,
) -> dict[str, Any]:
    """
    Call 1 (토크나이제이션) → Call 2 (매핑·가중치·컨텍스트 재구성) 전체 파이프라인.

    Returns:
        {
          "call1": { ... },   # tokenization result
          "call2": { ... },   # refined context
          "status": "OK" | "AMBIGUITY_HALT"
        }
    """
    # Call 1
    call1 = process_cra(raw_input, domain=domain, use_ai=use_ai)

    if call1.get("status") == "AMBIGUITY_HALT":
        return {"call1": call1, "call2": None, "status": "AMBIGUITY_HALT"}

    # Call 2
    call2 = (_ai_call2(call1) if use_ai else None) or _rule_based_call2(call1)

    return {"call1": call1, "call2": call2, "status": "OK"}


def _rule_based_call3(call2_result: dict, raw_input: str = "") -> dict:
    """AI 없이 Call 2 결과로 세 가지 출력을 생성하는 규칙 기반 폴백."""
    # call2가 {"call2": {...}} 형태로 넘어올 경우 대응
    if "call2" in call2_result and isinstance(call2_result.get("call2"), dict):
        call2_result = call2_result["call2"]
    ctx = call2_result.get("context", {})
    tokens = call2_result.get("refined_tokens", [])
    depth_summary = call2_result.get("depth_summary", {})

    primary = ctx.get("primary_focus", "주제 미확인")
    goals = ctx.get("inferred_goal", [])
    constraints = ctx.get("constraint_cluster", [])
    expert_state = ctx.get("expert_state", "unknown")
    peak_token = depth_summary.get("peak_token", "")
    avg_score = depth_summary.get("avg_score", 0.0)

    high_depth = [t for t in tokens if t.get("depth_score", 0) >= 0.7]

    # Output A — 전문가 브리핑
    goal_str = " / ".join(goals) if goals else "미확인"
    constraint_str = " / ".join(constraints) if constraints else "없음"
    token_str = ", ".join(f"{t['standard']}({t['depth_score']})" for t in high_depth)
    expert_output = (
        f"[전략 브리핑]\n"
        f"핵심 주제: {primary}\n"
        f"목표: {goal_str}\n"
        f"제약: {constraint_str}\n"
        f"현재 단계: {expert_state}\n"
        f"핵심 토큰(depth≥0.7): {token_str or '없음'}\n"
        f"Peak: {peak_token} ({depth_summary.get('peak_score', 0)}) / Avg: {avg_score}"
    )

    # Output B — 일반 사용자 요약
    patient_output = (
        f"## 지금 상황\n"
        f"지금 '{primary}'에 대해 정리가 필요한 상황입니다.\n\n"
        f"## 해야 할 것\n"
        + (f"'{goals[0]}'을 향해 구체적인 첫 단계를 설계해 보세요.\n" if goals else "목표를 명확히 정의하는 것이 첫 번째 단계입니다.\n")
        + f"\n## 주의할 것\n"
        + (f"'{constraints[0]}'은 반드시 고려해야 합니다.\n" if constraints else "현재 확인된 제약 조건을 기록해 두세요.\n")
    )

    # Output C — Before/After
    generic = (
        f"'{raw_input[:80]}...'에 대해 다음과 같이 접근할 수 있습니다. "
        f"먼저 목표를 설정하고, 관련 정보를 수집한 뒤, 단계별로 실행 계획을 세워보세요."
    ) if raw_input else "일반적인 AI 응답 예시"

    sage_pontus = (
        f"CRA 분석 결과: '{primary}' 단계에서 {expert_state} 상태로 확인됩니다. "
        f"depth≥0.7 핵심 토큰 {len(high_depth)}개 기반으로 "
        + (f"'{peak_token}' 중심의 실행 전략을 권장합니다." if peak_token else "구체적 전략을 설계합니다.")
    )

    quality_delta = (
        f"일반 AI는 원문을 그대로 받아 표면적 조언만 생성합니다. "
        f"Sage Pontus는 KB 기반 {len(high_depth)}개 핵심 토큰을 추출해 "
        f"depth_score 평균 {avg_score} 수준의 구조화된 컨텍스트로 변환합니다."
    )

    return {
        "expert_output": expert_output,
        "patient_output": patient_output,
        "before_after": {
            "generic_ai": generic,
            "sage_pontus": sage_pontus,
            "quality_delta": quality_delta,
        },
        "source": "rule",
    }


def _ai_call3(call2_result: dict) -> dict | None:
    """cra_call3.jinja 프롬프트로 AI 호출 → 세 가지 출력 반환."""
    if not _CRA_CALL3_TEMPLATE.exists():
        logger.warning("CRA Call3 템플릿 없음: %s", _CRA_CALL3_TEMPLATE)
        return None

    try:
        from jinja2 import Template
        tmpl = Template(_CRA_CALL3_TEMPLATE.read_text(encoding="utf-8"))
        prompt = tmpl.render(
            call2_result=json.dumps(call2_result, ensure_ascii=False, indent=2)
        )
    except Exception as e:
        logger.warning("CRA Call3 프롬프트 렌더 실패: %s", e)
        return None

    try:
        from questionnaire.prompts.service import _chat_generate
        raw_response = _chat_generate()(
            "gemini-2.0-flash",
            prompt,
            {"max_tokens": 2000, "temperature": 0.3},
        )
    except Exception as e:
        logger.warning("CRA Call3 AI 호출 실패: %s", e)
        return None

    text = raw_response.strip()
    if "```" in text:
        parts = text.split("```")
        text = parts[1] if len(parts) >= 2 else text
        text = re.sub(r"^json\s*", "", text).strip()

    try:
        result = json.loads(text)
        result["source"] = "ai"
        return result
    except json.JSONDecodeError as e:
        logger.warning("CRA Call3 JSON 파싱 실패: %s\n원문: %.200s", e, raw_response)
        return None


def _load_previous_context(user, domain: str | None) -> str | None:
    """
    직전 CRAAsset을 불러와 Call 1 프롬프트용 문자열로 반환.
    user=None 이면 None 반환.
    """
    if user is None:
        return None
    try:
        from questionnaire.models.models_braintree import CRAAsset
        qs = CRAAsset.objects.filter(user=user)
        if domain:
            qs = qs.filter(domain=domain)
        asset = qs.first()
        if not asset:
            return None
        return json.dumps({
            "domain": asset.domain,
            "context": asset.context,
            "depth_summary": asset.depth_summary,
            "expert_state": asset.expert_state,
            "tags": asset.tags,
            "session_date": asset.created_at.strftime("%Y-%m-%d"),
        }, ensure_ascii=False)
    except Exception as e:
        logger.debug("CRAAsset 로드 실패: %s", e)
        return None


def _save_cra_asset(user, braintree, domain: str | None, call2: dict) -> None:
    """Call 2 결과를 CRAAsset에 저장."""
    if user is None:
        return
    try:
        from questionnaire.models.models_braintree import CRAAsset
        ctx = call2.get("context", {})
        depth_summary = call2.get("depth_summary", {})
        expert_state = ctx.get("expert_state", "")
        # 태그: peak token + inferred_goal 앞 2개
        tags = []
        if depth_summary.get("peak_token"):
            tags.append(depth_summary["peak_token"])
        tags += (ctx.get("inferred_goal") or [])[:2]

        CRAAsset.objects.create(
            user=user,
            braintree=braintree,
            domain=domain or "",
            context=ctx,
            depth_summary=depth_summary,
            expert_state=expert_state,
            tags=tags,
        )
    except Exception as e:
        logger.warning("CRAAsset 저장 실패: %s", e)


def run_cra_pipeline(
    raw_input: str,
    domain: str | None = None,
    use_ai: bool = False,
    user=None,
    braintree=None,
) -> dict[str, Any]:
    """
    Call 1 → Call 2 → Call 3 전체 파이프라인.
    user를 넘기면 이전 세션 컨텍스트를 Call 1에 주입하고,
    Call 2 결과를 CRAAsset에 저장한다.

    Returns:
        {
          "call1": { ... },
          "call2": { ... },
          "call3": { ... },
          "status": "OK" | "AMBIGUITY_HALT",
          "continuity_hint": "이전 세션 연결 힌트 (있을 때만)"
        }
    """
    # 이전 세션 컨텍스트 로드
    previous_context = _load_previous_context(user, domain)

    # Call 1 (previous_context를 AI 모드에서 프롬프트에 주입)
    call1 = process_cra(
        raw_input,
        domain=domain,
        use_ai=use_ai,
        previous_context=previous_context,
    )
    if call1.get("status") == "AMBIGUITY_HALT":
        return {"call1": call1, "call2": None, "call3": None, "status": "AMBIGUITY_HALT"}

    # Call 2
    call2 = (_ai_call2(call1) if use_ai else None) or _rule_based_call2(call1)

    # Call 2 결과 저장
    _save_cra_asset(user, braintree, domain, call2)

    # Call 3
    call3 = (_ai_call3(call2) if use_ai else None) or _rule_based_call3(call2, raw_input)

    result: dict[str, Any] = {
        "call1": call1,
        "call2": call2,
        "call3": call3,
        "status": "OK",
    }
    if call1.get("continuity_hint"):
        result["continuity_hint"] = call1["continuity_hint"]
    return result


def enrich_qa_text(qa_text: str, domain: str | None = None) -> str:
    """
    service.py 파이프라인용: qa_pairs 텍스트에 KB 표준 용어를 인라인 주석으로 추가.

    예) "해결하고 싶은 문제가" → "해결하고 싶은 문제 [문제 정의 (Problem Statement)]가"
    """
    kb = load_kb(domain)

    # 긴 synonym 먼저 처리
    entries: list[tuple[str, str]] = []
    for kb_id, entry in kb.items():
        for syn in [entry["label"]] + entry.get("synonyms", []):
            entries.append((syn, entry["label"]))
    entries.sort(key=lambda x: len(x[0]), reverse=True)

    result = qa_text
    annotated_spans: list[tuple[int, int]] = []

    for synonym, label in entries:
        if synonym == label:
            continue  # label 자체는 이미 표준 용어이므로 주석 불필요
        idx = result.find(synonym)
        if idx == -1:
            continue
        end_idx = idx + len(synonym)
        if any(s <= idx < e or s < end_idx <= e for s, e in annotated_spans):
            continue
        annotation = f" [{label}]"
        result = result[:end_idx] + annotation + result[end_idx:]
        annotated_spans = [
            (s, e + len(annotation)) if s >= end_idx else (s, e)
            for s, e in annotated_spans
        ]
        annotated_spans.append((idx, end_idx + len(annotation)))

    return result
