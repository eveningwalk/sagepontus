"""버전 디렉터리의 manifest + Jinja 템플릿으로 프롬프트를 만들고 AI API로 생성.

GEMINI_API_KEY 환경 변수가 설정된 경우 Gemini를 사용하고,
그렇지 않으면 기존 Hugging Face Inference API를 사용한다.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml
from django.conf import settings
from jinja2 import Environment, FileSystemLoader


def _chat_generate():
    """ANTHROPIC_API_KEY → GEMINI_API_KEY → HF 순서로 클라이언트를 선택한다."""
    if os.environ.get("ANTHROPIC_API_KEY", "").strip():
        from questionnaire.prompts.claude_client import chat_completion_generate
    elif os.environ.get("GEMINI_API_KEY", "").strip():
        from questionnaire.prompts.gemini_client import chat_completion_generate
    else:
        from questionnaire.prompts.hf_client import chat_completion_generate
    return chat_completion_generate


def _chat_generate_with_usage():
    """(text, usage) 튜플을 반환하는 클라이언트를 선택한다.
    HF 클라이언트는 usage를 지원하지 않으므로 fallback으로 빈 usage를 반환하는 래퍼를 사용한다.
    """
    if os.environ.get("ANTHROPIC_API_KEY", "").strip():
        from questionnaire.prompts.claude_client import chat_completion_generate_with_usage
        return chat_completion_generate_with_usage
    if os.environ.get("GEMINI_API_KEY", "").strip():
        from questionnaire.prompts.gemini_client import chat_completion_generate_with_usage
        return chat_completion_generate_with_usage

    # HF fallback: usage 없이 텍스트만 반환하는 래퍼
    from questionnaire.prompts.hf_client import chat_completion_generate as _hf
    def _hf_with_usage(model_id, user, generation, *, system=None):
        text = _hf(model_id, user, generation, system=system)
        return text, {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    return _hf_with_usage


# 하위 호환: 직접 임포트한 곳이 있을 경우를 위해 모듈 수준 참조 유지
def chat_completion_generate(model_id, user, generation, *, system=None):
    return _chat_generate()(model_id, user, generation, system=system)

logger = logging.getLogger(__name__)

PROMPTS_ROOT = Path(__file__).resolve().parent / "versions"


def _available_versions() -> list[str]:
    if not PROMPTS_ROOT.is_dir():
        return []
    return sorted(
        p.name
        for p in PROMPTS_ROOT.iterdir()
        if p.is_dir() and (p / "manifest.yaml").is_file()
    )


def _resolve_version(requested: str | None) -> str:
    ver = (requested or getattr(settings, "PROMPT_VERSION", None) or "v1").strip()
    if ver in _available_versions():
        return ver
    if "v1" in _available_versions():
        logger.warning("프롬프트 버전 %s 없음 → v1 사용", ver)
        return "v1"
    raise FileNotFoundError(f"프롬프트 manifest 없음: {PROMPTS_ROOT}")


def _load_manifest(version: str) -> dict[str, Any]:
    path = PROMPTS_ROOT / version / "manifest.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _jinja_env(version: str) -> Environment:
    vdir = PROMPTS_ROOT / version
    return Environment(
        loader=FileSystemLoader(str(vdir)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )


# 도메인별 질문 중요도 프로파일 (질문 order 기반)
_DOMAIN_QUESTION_WEIGHTS: dict[str, dict[int, str]] = {
    "startup_bizplan": {
        1: "CRITICAL",  # 아이디어 한 줄 소개
        2: "MED",       # 배경 이야기
        3: "CRITICAL",  # 문제와 타겟
        4: "HIGH",      # 실현 방법
        5: "MED",       # 독자
        6: "MED",       # 강점/차별점
        7: "HIGH",      # 원하는 결과물
    },
}

# 도메인별 카테고리 중요도 프로파일 (카테고리 이름 기반)
_DOMAIN_CATEGORY_WEIGHTS: dict[str, dict[str, str]] = {
    "therapist_soap": {
        "therapist_soap": "CRITICAL",
        "common": "MED",
    },
}


def _get_weight(domain: str, order: int, cname: str) -> str:
    q_weights = _DOMAIN_QUESTION_WEIGHTS.get(domain, {})
    if q_weights:
        return q_weights.get(order, "")
    c_weights = _DOMAIN_CATEGORY_WEIGHTS.get(domain, {})
    return c_weights.get(cname, "")


def _format_qa_pairs(answers, domain: str = "") -> str:
    """답변이 모델에 잘 전달되도록 질문·분류·답변을 구조화."""
    parts: list[str] = []
    for i, a in enumerate(answers, 1):
        qtext = (a.question.question_text or "").strip()
        atext = (a.answer_text or "").strip()
        cat = getattr(a.question, "category", None)
        cname = (cat.name if cat else "") or "—"
        order = getattr(a.question, "order", i)
        weight = _get_weight(domain, order, cname)
        weight_tag = f" [중요도: {weight}]" if weight else ""
        parts.append(f"[{i}] 분류: {cname}{weight_tag}\n질문: {qtext}\n답변: {atext}")
    if not parts:
        return "(저장된 답변이 없습니다.)"
    return "\n\n".join(parts)


def _domain_focus(answers) -> str:
    """도메인(비공통) 카테고리 이름 — 마지막 비공통 분류를 우선."""
    last = ""
    for a in answers:
        cat = getattr(a.question, "category", None)
        if cat and cat.name and cat.name != "common":
            last = cat.name
    return last


def _format_extra_qa(extra_qa: list[dict]) -> str:
    """AI 보완 질문 답변을 포맷."""
    parts: list[str] = []
    for i, item in enumerate(extra_qa, 1):
        q = (item.get("q") or "").strip()
        a = (item.get("a") or "").strip()
        if q and a:
            parts.append(f"[AI보완-{i}] 분류: AI보완질문 [중요도: MED]\n질문: {q}\n답변: {a}")
    return "\n\n".join(parts)


def _format_user_qa(user_qa: list[dict]) -> str:
    """사용자 직접 추가 항목을 포맷 — 출력에 반드시 포함되어야 하는 내용."""
    parts: list[str] = []
    for i, item in enumerate(user_qa, 1):
        q = (item.get("q") or "").strip()
        a = (item.get("a") or "").strip()
        if q and a:
            parts.append(f"[사용자추가-{i}] [중요도: HIGH]\n제목: {q}\n내용: {a}")
    if not parts:
        return ""
    return "[사용자 추가 항목 — 계획서 본문에 반드시 포함]\n" + "\n\n".join(parts)


def _build_context(
    answers,
    extra_qa: list[dict] | None = None,
    distilled_context: dict | None = None,
    user_qa: list[dict] | None = None,
) -> dict[str, Any]:
    domain = _domain_focus(answers) or ""
    base = _format_qa_pairs(answers, domain=domain)

    if user_qa:
        user_extra = _format_user_qa(user_qa)
        if user_extra:
            base += "\n\n" + user_extra

    if extra_qa:
        extra = _format_extra_qa(extra_qa)
        if extra:
            base += "\n\n" + extra

    if distilled_context:
        lines = [f"- {k}: {v}" for k, v in distilled_context.items() if v]
        if lines:
            base += "\n\n[추가 컨텍스트 — brain dump에서 구조화된 보완 정보]\n" + "\n".join(lines)

    # CRA 전처리: 구어 → KB 표준 용어 인라인 주석 추가
    try:
        from questionnaire.prompts.cra_engine import enrich_qa_text
        base = enrich_qa_text(base, domain=domain or None)
    except Exception:
        logger.debug("CRA enrich 실패 — 원본 qa_pairs 사용", exc_info=True)

    return {
        "qa_pairs": base,
        "domain_focus": domain,
    }


_FOLLOWUP_SYSTEM = """당신은 AI 프롬프트 설계 전문가입니다.
사용자가 제공한 질문-답변을 분석하여, 최종 AI 프롬프트 생성에 꼭 필요하지만 아직 파악되지 않은 정보를 찾아내세요.
반드시 JSON 배열만 반환하고 다른 텍스트는 절대 포함하지 마세요."""

_FOLLOWUP_USER_TMPL = """아래는 사용자가 응답한 질문-답변 목록입니다:

{qa_pairs}

위 답변을 분석하여, 고품질 AI 프롬프트 생성을 위해 추가로 필요한 핵심 정보를 {count}개의 질문으로 만들어주세요.
각 질문은 앞선 답변에서 명확히 드러나지 않은 부분을 다뤄야 합니다.

아래 JSON 형식만 반환하세요 (마크다운 코드블록 없이):
[
  {{"text": "질문 내용", "hint": "답변 방향 힌트"}},
  {{"text": "질문 내용", "hint": "답변 방향 힌트"}},
  {{"text": "질문 내용", "hint": "답변 방향 힌트"}}
]"""


def generate_ai_followup_questions(answers, count: int = 3) -> list[dict]:
    """
    공통+도메인 답변을 분석해 AI 보완 질문 `count`개를 생성한다.
    반환: [{"order": 1, "text": "...", "hint": "..."}, ...]
    실패 시 빈 리스트 반환 (플로우 중단 없이 스킵).
    """
    import json as _json

    qa_pairs = _format_qa_pairs(answers)
    user_prompt = _FOLLOWUP_USER_TMPL.format(qa_pairs=qa_pairs, count=count)
    gen = {"max_tokens": 800, "temperature": 0.5}

    try:
        raw = _chat_generate()(
            "gemini-2.5-flash-lite",
            user_prompt,
            gen,
            system=_FOLLOWUP_SYSTEM,
        )
    except Exception as e:
        logger.exception("AI 보완 질문 생성 실패")
        return []

    # JSON 추출 (코드블록 감싸인 경우 처리)
    text = raw.strip()
    if "```" in text:
        text = text.split("```")[-2] if text.count("```") >= 2 else text
        text = text.lstrip("json").strip()

    try:
        items = _json.loads(text)
        if not isinstance(items, list):
            raise ValueError("list 형식이 아닙니다")
        result = []
        for i, item in enumerate(items[:count], 1):
            result.append({
                "order": i,
                "text": str(item.get("text") or "").strip(),
                "hint": str(item.get("hint") or "").strip(),
            })
        return result
    except Exception as e:
        logger.warning("AI 보완 질문 JSON 파싱 실패: %s\n원문: %s", e, raw[:300])
        return []


def _render_task(env: Environment, filename: str, ctx: dict[str, Any]) -> str:
    t = env.get_template(filename)
    return t.render(**ctx).strip()


def _run_task(
    version: str,
    manifest: dict[str, Any],
    task_key: str,
    ctx: dict[str, Any],
    model_id: str,
) -> str:
    tasks = manifest.get("tasks") or {}
    spec = tasks.get(task_key) or {}
    user_file = spec.get("user")
    if not user_file:
        raise KeyError(f"manifest tasks.{task_key} 에 user 가 없습니다.")

    env = _jinja_env(version)
    user = _render_task(env, user_file, ctx)

    system_file = spec.get("system")
    system: str | None = None
    if system_file:
        system = _render_task(env, str(system_file), ctx).strip() or None

    if (manifest.get("api") or "chat") != "chat":
        raise NotImplementedError("현재는 api: chat 만 지원합니다.")

    gen = dict(manifest.get("generation") or {})
    task_gen = spec.get("generation")
    if isinstance(task_gen, dict):
        gen.update(task_gen)
    return _chat_generate()(model_id, user, gen, system=system)


def run_prompt_generation_pair(answers, extra_qa: list[dict] | None = None) -> tuple[str, str]:
    """
    설문 답변을 바탕으로 (실행 관점 요약, 다른 LLM에 붙여 넣을 프롬프트 본문)을 생성한다.
    HF 또는 템플릿 오류 시 사용자에게 보일 한국어 메시지로 대체.
    """
    version = _resolve_version(getattr(settings, "PROMPT_VERSION", None))
    try:
        manifest = _load_manifest(version)
    except Exception as e:
        logger.exception("manifest 로드 실패")
        err = f"[프롬프트 설정 오류] manifest 를 읽을 수 없습니다: {e}"
        return err, err

    model_id = (getattr(settings, "HF_MODEL_ID", None) or "").strip() or (manifest.get("model") or "").strip()
    if not model_id:
        err = "[설정 오류] manifest.model 또는 설정 HF_MODEL_ID 가 필요합니다."
        return err, err

    ctx = _build_context(answers, extra_qa=extra_qa)

    def safe_task(key: str) -> str:
        try:
            return _run_task(version, manifest, key, ctx, model_id)
        except Exception as e:
            provider = "Gemini" if os.environ.get("GEMINI_API_KEY", "").strip() else "Hugging Face"
            logger.exception("%s 생성 실패 task=%s", provider, key)
            return (
                f"[AI 생성 실패] {provider} API 호출 중 오류가 났습니다.\n상세: {e!s}"
            )

    return safe_task("strategy"), safe_task("prompt_builder")


def run_single_task(
    task_key: str,
    answers,
    extra_qa: list[dict] | None = None,
    distilled_context: dict | None = None,
    user_qa: list[dict] | None = None,
) -> str:
    """strategy 또는 prompt_builder 태스크를 단독 실행 (SSE 스트림용)."""
    version = _resolve_version(getattr(settings, "PROMPT_VERSION", None))
    try:
        manifest = _load_manifest(version)
    except Exception as e:
        return f"[프롬프트 설정 오류] manifest 를 읽을 수 없습니다: {e}"
    model_id = (getattr(settings, "HF_MODEL_ID", None) or "").strip() or (manifest.get("model") or "").strip()
    if not model_id:
        return "[설정 오류] manifest.model 또는 설정 HF_MODEL_ID 가 필요합니다."
    ctx = _build_context(answers, extra_qa=extra_qa, distilled_context=distilled_context, user_qa=user_qa)
    try:
        return _run_task(version, manifest, task_key, ctx, model_id)
    except Exception as e:
        provider = "Gemini" if os.environ.get("GEMINI_API_KEY", "").strip() else "Hugging Face"
        logger.exception("%s 생성 실패 task=%s", provider, task_key)
        return f"[AI 생성 실패] {provider} API 호출 중 오류가 났습니다.\n상세: {e!s}"


_SOAP_DOMAINS = frozenset({"therapist_soap"})
# 공통 질문을 건너뛰는 도메인 (SOAP + startup_bizplan)
_SKIP_COMMON_DOMAINS = _SOAP_DOMAINS | frozenset({"startup_bizplan"})

_SOAP_NOTE_SYSTEM_BASE = """\
당신은 Sage Pontus의 "물리치료 케이스 컨텍스트 프롬프트 작성기"다.

[목표]
물리치료사가 입력한 환자 SOAP 정보를 바탕으로, 다른 AI·챗봇에 붙여 넣을 수 있는 구조화된 환자 컨텍스트 시스템 프롬프트를 한국어로 작성한다.

이 프롬프트의 목적: PT가 새 AI 세션을 열 때마다 환자 상황을 처음부터 설명하지 않아도 되도록, 핵심 임상 맥락을 압축해서 전달하는 것이다.

[처리 규칙]
- 치료사 컨텍스트(시스템에 제공됨) → # 역할과 상황 섹션에 반영: 근무 환경·전문 영역·주요 환자군·치료 접근법을 구체적으로 기술한다.
- 환자 SOAP 정보 → # 환자 임상 정보 섹션에 반영: S/O/A/P 네 섹션을 반드시 모두 포함한다.
- 구어체·비표준 표현을 임상 표준 문어체로 정제한다.
- 입력에 없는 내용은 절대 추가하지 않는다. 정보가 없는 항목은 "미측정" 또는 "해당 없음"으로 표기한다.
- 전문 약어를 적절히 사용한다 (ROM, MMT, NRS, ADL, DTR, LTG, STG, VAS 등).
- 각 섹션은 2~5문장으로 간결하게 압축한다.

[중요도 처리]
- CRITICAL: 반드시 출력에 포함. 생략·축약 불가
- HIGH: 출력에 포함. 핵심만 압축 가능
- MED: 관련 섹션에 반영. 공간 부족 시 생략 가능

[금지]
- 질문:/답변: 라벨, 번호 매기기, 설문 원문 그대로 나열.
- 메타 설명 ("아래는 프롬프트입니다" 등).
- 입력에 없는 수치·사실 추가.

[출력 형식 — 아래 전체 구조를 반드시 출력한다. 중간에 멈추지 않는다]

# 역할과 상황
당신은 숙련된 물리치료 전문가 AI입니다. 아래는 현재 치료 진행 중인 환자의 임상 정보입니다. 이 맥락을 바탕으로 담당 물리치료사의 임상 판단을 전문적으로 지원합니다.

# 환자 임상 정보

## S (Subjective) — 환자 주관적 정보
[통증 부위·양상·NRS, 병력·발병일, ADL 제한, 환자 목표를 임상 문어체로 정제]

## O (Objective) — 객관적 검사 결과
[ROM, MMT, Special Tests, 자세·촉진, 신경학적 검사 결과를 임상 문어체로 정제]

## A (Assessment) — 임상적 추론
[Problem List, 치료 가설, 예후 예측을 임상 문어체로 정제]

## P (Plan) — 치료 계획
[LTG/STG, 오늘 치료 내용, 차기 세션 계획을 임상 문어체로 정제]

# 기대 응답 방식
이 환자의 임상 맥락을 완전히 파악한 상태에서 답변하세요. 치료 방향·운동 처방·주의사항·예후에 대한 질문에 근거 기반 물리치료 전문 지식으로 답변하세요. 의사 의뢰가 필요한 사항은 즉시 언급하세요.
"""


def _build_profile_context(profile_answers) -> str:
    """PT 프로필 답변을 system prompt에 삽입할 치료사 컨텍스트 블록으로 변환."""
    if not profile_answers:
        return ""
    lines = []
    for a in profile_answers:
        qtext = (a.question.question_text or "").strip()
        atext = (a.answer_text or "").strip()
        if qtext and atext:
            lines.append(f"- {qtext}: {atext}")
    if not lines:
        return ""
    block = "\n".join(lines)
    return f"\n\n[치료사 컨텍스트 — # 역할과 상황 섹션에 반영]\n{block}"


_SOAP_NOTE_USER_TMPL = """\
아래 환자 SOAP 정보를 바탕으로 AI 시스템 프롬프트를 작성해 주세요.

{soap_pairs}
"""


_SOAP_WARNING_SYSTEM = """\
당신은 물리치료 임상 안전 전문가입니다. 입력된 SOAP 정보에서 즉각적인 의사 의뢰가 필요한 위험 신호(Red Flag)를 탐지합니다.

[탐지 기준]
1. Cauda Equina 증후군: 대소변 기능 장애, 안장 마취(saddle anesthesia)
2. 상위 운동 신경원 징후: Babinski 양성, 반사항진, 경직
3. 악성 종양 의심: 원인 불명 체중 감소, 야간 안정 통증, 암 병력
4. 골절 의심: 심각한 외상, 골다공증 + 낙상, 극심한 국소 압통
5. 심혈관 이상: 운동 시 흉통, 턱·좌상지 방사통, 안정 시 호흡곤란
6. 진행성 신경학적 결손: 점진적 근력 저하 진행, 완전 감각 소실
7. 감염 의심: 발열 동반, 최근 감염 이력, 면역 억제 상태
8. 척추 불안정성: 심각한 외상 후 상태, 인대 파열
9. 소견서 없이 치료 불가 케이스: 수술 후 미승인 상태, 급성 외상 영상 미확인, 진단명 없는 급성 중증 증상

[반환 형식 — JSON만, 마크다운 코드블록 없이]
{
  "level": "danger" | "caution" | "safe",
  "flags": ["탐지된 위험 신호 설명 (한국어, 1~2문장)", ...],
  "recommendation": "권고 조치 (한 문장)"
}

[level 기준]
- danger: 즉시 치료 중단 + 의사 의뢰 필수
- caution: 치료 진행 가능하나 의사 확인 강력 권장
- safe: 탐지된 위험 신호 없음, 정상 PT 범위
"""

_SOAP_WARNING_USER_TMPL = """\
아래 SOAP 정보를 분석하여 Red Flag 위험 신호를 탐지하고 JSON으로 반환하세요.

{qa_pairs}
"""


def generate_soap_warning(answers) -> dict:
    """SOAP 답변에서 Red Flag를 탐지해 위험 수준과 권고를 반환한다."""
    import json as _json

    qa_pairs = _format_qa_pairs(answers)
    user_prompt = _SOAP_WARNING_USER_TMPL.format(qa_pairs=qa_pairs)
    gen = {"max_tokens": 600, "temperature": 0.1}

    try:
        raw = _chat_generate()(
            "gemini-2.5-flash-lite",
            user_prompt,
            gen,
            system=_SOAP_WARNING_SYSTEM,
        )
    except Exception as e:
        logger.warning("Warning alarm 생성 실패: %s", e)
        return {"level": "unknown", "flags": [], "recommendation": "분석 실패 — 임상 판단으로 확인하세요."}

    try:
        return _json.loads(raw)
    except Exception:
        try:
            from questionnaire.prompts.cra_engine import _extract_json
            return _json.loads(_extract_json(raw))
        except Exception:
            logger.warning("Warning alarm JSON 파싱 실패. raw=%s", raw[:200])
            return {"level": "unknown", "flags": [], "recommendation": raw[:150]}


def generate_soap_note(answers, profile_answers=None, extra_qa: list[dict] | None = None) -> str:
    """therapist_soap 도메인 전용 SOAP 노트 생성."""
    soap_pairs = _format_qa_pairs(answers, domain="therapist_soap")
    if extra_qa:
        extra = _format_extra_qa(extra_qa)
        if extra:
            soap_pairs += "\n\n" + extra

    system = _SOAP_NOTE_SYSTEM_BASE + _build_profile_context(profile_answers)
    user_prompt = _SOAP_NOTE_USER_TMPL.format(soap_pairs=soap_pairs)
    gen = {"max_tokens": 4000, "temperature": 0.3}

    try:
        return _chat_generate()(
            "gemini-2.5-flash",
            user_prompt,
            gen,
            system=system,
        )
    except Exception as e:
        logger.exception("SOAP 노트 생성 실패")
        return f"[SOAP 노트 생성 실패] AI 호출 중 오류가 발생했습니다.\n상세: {e!s}"


_AUTOFILL_SYSTEM = "당신은 사용자의 메모(brain dump)를 분석해 구조화된 질문지에 답변을 채워주는 전문가입니다."

_AUTOFILL_USER_TMPL = """\
아래는 사용자가 자유롭게 작성한 메모(brain dump)입니다.

[메모]
{brain_dump}

이 메모를 바탕으로 아래 질문들에 대한 답변을 작성해 주세요.
메모에 관련 내용이 없는 질문은 빈 문자열("")로 답변하세요.
각 답변은 메모에서 추출하거나 합리적으로 추론한 내용만 포함하고, 없는 내용은 지어내지 마세요.

[질문 목록]
{questions}

아래 JSON 형식만 반환하세요 (마크다운 코드블록 없이):
{{"answers": [{{"id": <질문ID>, "answer": "<답변 텍스트>"}}, ...]}}"""


_DISTILL_SYSTEM = """당신은 창업 메모를 분석해 비즈니스 인사이트를 추출하는 전문가입니다.
반드시 JSON 객체만 반환하고 다른 텍스트는 절대 포함하지 마세요."""

_DISTILL_USER_TMPL = """\
아래는 사용자가 작성한 메모(brain dump)와, 이미 구조화된 질문-답변 목록입니다.

[메모 원문]
{brain_dump}

[이미 구조화된 답변]
{autofill_qa}

구조화된 답변에 이미 반영된 내용을 제외하고,
메모에서 추가로 발견되는 비즈니스 인사이트를 아래 차원으로 추출해주세요.
해당 정보가 없으면 해당 키를 포함하지 마세요.

아래 JSON 형식만 반환하세요 (마크다운 코드블록 없이):
{{
  "경쟁_환경": "경쟁사·시장 현황",
  "팀_역량": "창업팀 배경·경험",
  "외부_기회": "정부지원·트렌드·파트너십",
  "수익_모델": "수익 구조·BM",
  "리스크": "예상 리스크·제약",
  "기타_맥락": "위 항목에 속하지 않는 유의미한 정보"
}}"""


def distill_extra_context(brain_dump: str, autofill_qa: list[dict]) -> dict:
    """
    brain dump에서 autofill로 추출된 Q&A 외 잔여 비즈니스 인사이트를 구조화해 반환한다.
    autofill_qa: [{"q": "질문", "a": "답변"}, ...]
    반환: {"경쟁_환경": "...", "팀_역량": "...", ...}  빈 항목은 제외.
    실패 시 빈 dict 반환.
    """
    import json as _json

    if not brain_dump.strip():
        return {}

    qa_text = "\n".join(f"- {item['q']}: {item['a']}" for item in autofill_qa if item.get("a"))
    user_prompt = _DISTILL_USER_TMPL.format(
        brain_dump=brain_dump.strip(),
        autofill_qa=qa_text or "(없음)",
    )
    gen = {"max_tokens": 800, "temperature": 0.3}

    try:
        raw = _chat_generate()(
            "gemini-2.5-flash-lite",
            user_prompt,
            gen,
            system=_DISTILL_SYSTEM,
        )
    except Exception:
        logger.exception("distill_extra_context AI 호출 실패")
        return {}

    text = raw.strip()
    if "```" in text:
        parts = text.split("```")
        text = parts[1] if len(parts) >= 2 else text
        text = text.lstrip("json").strip()

    try:
        result = _json.loads(text)
        if not isinstance(result, dict):
            return {}
        return {k: v for k, v in result.items() if v and str(v).strip()}
    except Exception:
        logger.warning("distill_extra_context JSON 파싱 실패. raw=%s", raw[:300])
        return {}


def autofill_answers_from_brain_dump(brain_dump: str, questions: list[dict]) -> dict[int, str]:
    """
    brain dump 텍스트에서 각 질문에 대한 답변을 AI로 생성한다.
    questions: [{"id": int, "text": str, "category": str}, ...]
    반환: {question_id: answer_text}  (실패 시 빈 dict)
    """
    import json as _json

    if not brain_dump.strip() or not questions:
        return {}

    q_lines = "\n".join(
        f"- ID {q['id']} [{q['category']}] {q['text']}" for q in questions
    )
    user_prompt = _AUTOFILL_USER_TMPL.format(
        brain_dump=brain_dump.strip(),
        questions=q_lines,
    )
    gen = {"max_tokens": 2000, "temperature": 0.3}

    try:
        raw = _chat_generate()(
            "gemini-2.5-flash-lite",
            user_prompt,
            gen,
            system=_AUTOFILL_SYSTEM,
        )
    except Exception as e:
        logger.warning("autofill AI 호출 실패: %s", e)
        return {}

    try:
        data = _json.loads(raw)
        return {int(item["id"]): item["answer"] for item in data.get("answers", [])}
    except Exception:
        # JSON 파싱 실패 시 _extract_json 시도
        try:
            from questionnaire.prompts.cra_engine import _extract_json
            data = _json.loads(_extract_json(raw))
            return {int(item["id"]): item["answer"] for item in data.get("answers", [])}
        except Exception:
            logger.warning("autofill JSON 파싱 실패. raw=%s", raw[:200])
            return {}
