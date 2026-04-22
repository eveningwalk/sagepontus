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


def _format_qa_pairs(answers) -> str:
    """답변이 모델에 잘 전달되도록 질문·분류·답변을 구조화."""
    parts: list[str] = []
    for i, a in enumerate(answers, 1):
        qtext = (a.question.question_text or "").strip()
        atext = (a.answer_text or "").strip()
        cat = getattr(a.question, "category", None)
        cname = (cat.name if cat else "") or "—"
        parts.append(f"[{i}] 분류: {cname}\n질문: {qtext}\n답변: {atext}")
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
            parts.append(f"[AI보완-{i}] 분류: AI보완질문\n질문: {q}\n답변: {a}")
    return "\n\n".join(parts)


def _build_context(answers, extra_qa: list[dict] | None = None) -> dict[str, Any]:
    base = _format_qa_pairs(answers)
    if extra_qa:
        extra = _format_extra_qa(extra_qa)
        if extra:
            base += "\n\n" + extra

    domain = _domain_focus(answers) or None

    # CRA 전처리: 구어 → KB 표준 용어 인라인 주석 추가
    try:
        from questionnaire.prompts.cra_engine import enrich_qa_text
        base = enrich_qa_text(base, domain=domain)
    except Exception:
        logger.debug("CRA enrich 실패 — 원본 qa_pairs 사용", exc_info=True)

    return {
        "qa_pairs": base,
        "domain_focus": domain or "",
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


def run_single_task(task_key: str, answers, extra_qa: list[dict] | None = None) -> str:
    """strategy 또는 prompt_builder 태스크를 단독 실행 (SSE 스트림용)."""
    version = _resolve_version(getattr(settings, "PROMPT_VERSION", None))
    try:
        manifest = _load_manifest(version)
    except Exception as e:
        return f"[프롬프트 설정 오류] manifest 를 읽을 수 없습니다: {e}"
    model_id = (getattr(settings, "HF_MODEL_ID", None) or "").strip() or (manifest.get("model") or "").strip()
    if not model_id:
        return "[설정 오류] manifest.model 또는 설정 HF_MODEL_ID 가 필요합니다."
    ctx = _build_context(answers, extra_qa=extra_qa)
    try:
        return _run_task(version, manifest, task_key, ctx, model_id)
    except Exception as e:
        provider = "Gemini" if os.environ.get("GEMINI_API_KEY", "").strip() else "Hugging Face"
        logger.exception("%s 생성 실패 task=%s", provider, task_key)
        return f"[AI 생성 실패] {provider} API 호출 중 오류가 났습니다.\n상세: {e!s}"
