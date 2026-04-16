"""Anthropic Claude API 호출 (Messages API)."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

_CLAUDE_BASE_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"
_DEFAULT_MODEL = "claude-sonnet-4-20250514"


def _api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY 환경 변수가 설정되지 않았습니다. "
            ".env 파일에 ANTHROPIC_API_KEY=<your-key> 를 추가하세요."
        )
    return key


def _model_id(requested: str) -> str:
    override = os.environ.get("CLAUDE_MODEL_ID", "").strip()
    if override:
        return override
    # HF 형식(슬래시 포함) 또는 Gemini 모델명은 Claude에서 사용 불가 → 기본 모델로 대체
    if "/" in requested or requested.startswith("gemini"):
        logger.debug("모델 ID '%s' 감지 → Claude 기본 모델 '%s' 사용", requested, _DEFAULT_MODEL)
        return _DEFAULT_MODEL
    return requested or _DEFAULT_MODEL


def chat_completion_generate(
    model_id: str,
    user: str,
    generation: dict[str, Any],
    *,
    system: str | None = None,
) -> str:
    """
    Anthropic Messages API 호출.
    gemini_client.chat_completion_generate 와 동일한 시그니처.
    """
    api_key = _api_key()
    model = _model_id(model_id)

    payload: dict[str, Any] = {
        "model": model,
        "max_tokens": int(generation.get("max_tokens", 1000)),
        "messages": [{"role": "user", "content": user}],
    }
    if system and system.strip():
        payload["system"] = system.strip()

    top_p = generation.get("top_p")
    temperature = generation.get("temperature")
    if top_p is not None:
        payload["top_p"] = float(top_p)
    if temperature is not None:
        payload["temperature"] = float(temperature)

    headers = {
        "x-api-key": api_key,
        "anthropic-version": _ANTHROPIC_VERSION,
        "Content-Type": "application/json",
    }

    logger.debug("Claude 호출: model=%s", model)
    try:
        resp = requests.post(_CLAUDE_BASE_URL, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
    except requests.HTTPError as e:
        code = e.response.status_code if e.response is not None else None
        if code in (401, 403):
            raise RuntimeError(
                f"Claude API 인증 실패({code}). ANTHROPIC_API_KEY 값을 확인하세요."
            ) from e
        if code == 404:
            raise RuntimeError(
                f"Claude 모델 '{model}'을 찾을 수 없습니다(404). "
                "CLAUDE_MODEL_ID 환경 변수로 올바른 모델명을 지정하세요."
            ) from e
        raise RuntimeError(f"Claude API 오류({code}): {e}") from e
    except requests.RequestException as e:
        raise RuntimeError(f"Claude 네트워크 오류: {e}") from e

    data = resp.json()
    try:
        content = data["content"][0]["text"]
    except (KeyError, IndexError, TypeError) as e:
        raise TypeError(f"Claude 응답 형식 오류: {json.dumps(data)[:200]}") from e

    return (content or "").strip()


def chat_completion_generate_with_usage(
    model_id: str,
    user: str,
    generation: dict[str, Any],
    *,
    system: str | None = None,
) -> tuple[str, dict]:
    """
    chat_completion_generate 와 동일하나 (text, usage) 튜플을 반환한다.
    usage = {"input_tokens": int, "output_tokens": int, "total_tokens": int}
    """
    api_key = _api_key()
    model = _model_id(model_id)

    payload: dict[str, Any] = {
        "model": model,
        "max_tokens": int(generation.get("max_tokens", 1000)),
        "messages": [{"role": "user", "content": user}],
    }
    if system and system.strip():
        payload["system"] = system.strip()

    top_p = generation.get("top_p")
    temperature = generation.get("temperature")
    if top_p is not None:
        payload["top_p"] = float(top_p)
    if temperature is not None:
        payload["temperature"] = float(temperature)

    headers = {
        "x-api-key": api_key,
        "anthropic-version": _ANTHROPIC_VERSION,
        "Content-Type": "application/json",
    }

    logger.debug("Claude 호출(usage): model=%s", model)
    try:
        resp = requests.post(_CLAUDE_BASE_URL, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
    except requests.HTTPError as e:
        code = e.response.status_code if e.response is not None else None
        if code in (401, 403):
            raise RuntimeError(
                f"Claude API 인증 실패({code}). ANTHROPIC_API_KEY 값을 확인하세요."
            ) from e
        if code == 404:
            raise RuntimeError(
                f"Claude 모델 '{model}'을 찾을 수 없습니다(404). "
                "CLAUDE_MODEL_ID 환경 변수로 올바른 모델명을 지정하세요."
            ) from e
        raise RuntimeError(f"Claude API 오류({code}): {e}") from e
    except requests.RequestException as e:
        raise RuntimeError(f"Claude 네트워크 오류: {e}") from e

    data = resp.json()
    try:
        content = data["content"][0]["text"]
    except (KeyError, IndexError, TypeError) as e:
        raise TypeError(f"Claude 응답 형식 오류: {json.dumps(data)[:200]}") from e

    raw_usage = data.get("usage") or {}
    input_tokens = int(raw_usage.get("input_tokens", 0))
    output_tokens = int(raw_usage.get("output_tokens", 0))
    usage = {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }
    return (content or "").strip(), usage
