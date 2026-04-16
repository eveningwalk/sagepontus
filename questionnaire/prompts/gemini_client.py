"""Google Gemini API 호출 (OpenAI 호환 엔드포인트 — 추가 패키지 불필요)."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

import requests

logger = logging.getLogger(__name__)

_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
_DEFAULT_MODEL = "gemini-2.0-flash"


def _api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "GEMINI_API_KEY 환경 변수가 설정되지 않았습니다. "
            ".env 파일에 GEMINI_API_KEY=<your-key> 를 추가하세요. "
            "(https://aistudio.google.com/apikey 에서 발급)"
        )
    return key


def _model_id(requested: str) -> str:
    """
    manifest의 model 값이 HF 형식(예: Qwen/...)이면 무시하고
    GEMINI_MODEL_ID 또는 기본값을 사용한다.
    """
    override = os.environ.get("GEMINI_MODEL_ID", "").strip()
    if override:
        return override
    # HF 형식 모델 ID(슬래시 포함)는 Gemini에서 사용 불가 → 기본 모델로 대체
    if "/" in requested:
        logger.debug("HF 모델 ID '%s' 감지 → Gemini 기본 모델 '%s' 사용", requested, _DEFAULT_MODEL)
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
    Gemini OpenAI 호환 /chat/completions 엔드포인트 호출.
    hf_client.chat_completion_generate 와 동일한 시그니처.
    """
    api_key = _api_key()
    model = _model_id(model_id)

    messages: list[dict[str, str]] = []
    if system and system.strip():
        messages.append({"role": "system", "content": system.strip()})
    messages.append({"role": "user", "content": user})

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": int(generation.get("max_tokens", 512)),
        "temperature": float(generation.get("temperature", 0.7)),
    }
    top_p = generation.get("top_p")
    if top_p is not None:
        payload["top_p"] = float(top_p)

    url = f"{_GEMINI_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    logger.debug("Gemini 호출: model=%s url=%s", model, url)
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
    except requests.HTTPError as e:
        code = e.response.status_code if e.response is not None else None
        if code == 401 or code == 403:
            raise RuntimeError(
                f"Gemini API 인증 실패({code}). GEMINI_API_KEY 값을 확인하세요."
            ) from e
        if code == 404:
            raise RuntimeError(
                f"Gemini 모델 '{model}'을 찾을 수 없습니다(404). "
                "GEMINI_MODEL_ID 환경 변수로 올바른 모델명을 지정하세요 "
                "(예: gemini-2.0-flash, gemini-1.5-pro)."
            ) from e
        raise RuntimeError(f"Gemini API 오류({code}): {e}") from e
    except requests.RequestException as e:
        raise RuntimeError(f"Gemini 네트워크 오류: {e}") from e

    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise TypeError(f"Gemini 응답 형식 오류: {json.dumps(data)[:200]}") from e

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

    messages: list[dict[str, str]] = []
    if system and system.strip():
        messages.append({"role": "system", "content": system.strip()})
    messages.append({"role": "user", "content": user})

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": int(generation.get("max_tokens", 512)),
        "temperature": float(generation.get("temperature", 0.7)),
    }
    top_p = generation.get("top_p")
    if top_p is not None:
        payload["top_p"] = float(top_p)

    url = f"{_GEMINI_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    logger.debug("Gemini 호출(usage): model=%s url=%s", model, url)
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
        resp.raise_for_status()
    except requests.HTTPError as e:
        code = e.response.status_code if e.response is not None else None
        if code == 401 or code == 403:
            raise RuntimeError(
                f"Gemini API 인증 실패({code}). GEMINI_API_KEY 값을 확인하세요."
            ) from e
        if code == 404:
            raise RuntimeError(
                f"Gemini 모델 '{model}'을 찾을 수 없습니다(404). "
                "GEMINI_MODEL_ID 환경 변수로 올바른 모델명을 지정하세요."
            ) from e
        raise RuntimeError(f"Gemini API 오류({code}): {e}") from e
    except requests.RequestException as e:
        raise RuntimeError(f"Gemini 네트워크 오류: {e}") from e

    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise TypeError(f"Gemini 응답 형식 오류: {json.dumps(data)[:200]}") from e

    raw_usage = data.get("usage") or {}
    usage = {
        "input_tokens": int(raw_usage.get("prompt_tokens", 0)),
        "output_tokens": int(raw_usage.get("completion_tokens", 0)),
        "total_tokens": int(raw_usage.get("total_tokens", 0)),
    }
    return (content or "").strip(), usage
