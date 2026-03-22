"""버전 디렉터리의 manifest + Jinja 템플릿으로 프롬프트를 만들고 HF API로 생성."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from django.conf import settings
from jinja2 import Environment, FileSystemLoader

from questionnaire.prompts.hf_client import chat_completion_generate

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


def _build_context(answers) -> dict[str, Any]:
    return {
        "qa_pairs": _format_qa_pairs(answers),
        "domain_focus": _domain_focus(answers),
    }


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
    return chat_completion_generate(model_id, user, gen, system=system)


def run_prompt_generation_pair(answers) -> tuple[str, str]:
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

    ctx = _build_context(answers)

    def safe_task(key: str) -> str:
        try:
            return _run_task(version, manifest, key, ctx, model_id)
        except Exception as e:
            logger.exception("HF 생성 실패 task=%s", key)
            return (
                f"[AI 생성 실패] Hugging Face API 호출 중 오류가 났습니다. "
                f"네트워크·모델 ID·HF_TOKEN(필요 시)을 확인하세요.\n상세: {e!s}"
            )

    return safe_task("strategy"), safe_task("prompt_builder")
