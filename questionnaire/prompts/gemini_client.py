"""Google Gemini API 호출 (OpenAI 호환 엔드포인트 — 추가 패키지 불필요)."""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

import requests

logger = logging.getLogger(__name__)

_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
_DEFAULT_MODEL = "gemini-2.0-flash"
_MAX_RETRIES = 3
_FALLBACK_HF_MODEL = "meta-llama/Llama-3.3-70B-Instruct"

# 429 폴백 발생 후 다음 Gemini 호출에 사용할 모델 (프로세스 수명 동안 유지)
_next_gemini_model: str | None = None


class GeminiRateLimitError(RuntimeError):
    """Gemini 429 재시도 한도 초과."""


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
    override = os.environ.get("GEMINI_MODEL_ID", "").strip()
    if override:
        return override
    if "/" in requested:
        logger.debug("HF 모델 ID '%s' 감지 → Gemini 기본 모델 '%s' 사용", requested, _DEFAULT_MODEL)
        return _DEFAULT_MODEL
    return requested or _DEFAULT_MODEL


def _post_with_retry(url: str, headers: dict, payload: dict) -> requests.Response:
    """429 시 exponential backoff 재시도 (최대 3회). 3회 모두 실패 시 GeminiRateLimitError."""
    for attempt in range(_MAX_RETRIES + 1):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            if resp.status_code == 429:
                if attempt == _MAX_RETRIES:
                    raise GeminiRateLimitError(
                        f"Gemini 429 재시도 한도({_MAX_RETRIES}회) 초과"
                    )
                retry_after = int(resp.headers.get("Retry-After", 0))
                wait = retry_after if retry_after > 0 else 2 ** (attempt + 1)
                logger.warning("Gemini 429 — %d초 후 재시도 (%d/%d)", wait, attempt + 1, _MAX_RETRIES)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp
        except GeminiRateLimitError:
            raise
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else None
            if code == 401 or code == 403:
                raise RuntimeError(
                    f"Gemini API 인증 실패({code}). GEMINI_API_KEY 값을 확인하세요."
                ) from e
            if code == 404:
                raise RuntimeError(
                    f"Gemini 모델을 찾을 수 없습니다(404). "
                    "GEMINI_MODEL_ID 환경 변수로 올바른 모델명을 지정하세요."
                ) from e
            raise RuntimeError(f"Gemini API 오류({code}): {e}") from e
        except requests.RequestException as e:
            raise RuntimeError(f"Gemini 네트워크 오류: {e}") from e
    raise GeminiRateLimitError("Gemini API 재시도 한도 초과 (429)")


def _build_payload(model_id: str, user: str, generation: dict, system: str | None) -> tuple[str, dict, dict]:
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
        "Authorization": f"Bearer {_api_key()}",
        "Content-Type": "application/json",
    }
    return url, headers, payload


def _hf_fallback(user: str, generation: dict[str, Any], system: str | None) -> str:
    """Gemini 429 한도 초과 시 HF Llama-3.3-70B 로 1회 폴백."""
    global _next_gemini_model
    _next_gemini_model = "gemini-2.5-flash"
    logger.warning(
        "Gemini 429 한도 초과 → HF %s 폴백 (다음 Gemini 호출은 gemini-2.5-flash 사용)",
        _FALLBACK_HF_MODEL,
    )
    try:
        from questionnaire.prompts.hf_client import chat_completion_generate as _hf
        return _hf(_FALLBACK_HF_MODEL, user, generation, system=system)
    except Exception as hf_e:
        raise RuntimeError(
            f"Gemini 429 한도 초과 후 HuggingFace({_FALLBACK_HF_MODEL}) 폴백도 실패했습니다. "
            f"잠시 후 다시 시도해 주세요.\n상세: {hf_e}"
        ) from hf_e


def _resolve_model_with_state(model_id: str) -> str:
    """429 폴백 후 지정된 모델이 있으면 그것을 사용하고 상태를 초기화."""
    global _next_gemini_model
    if _next_gemini_model:
        resolved = _next_gemini_model
        _next_gemini_model = None
        logger.info("이전 429 폴백 후 첫 Gemini 재호출 → %s 사용", resolved)
        return resolved
    return model_id


def chat_completion_generate(
    model_id: str,
    user: str,
    generation: dict[str, Any],
    *,
    system: str | None = None,
) -> str:
    effective_model = _resolve_model_with_state(model_id)
    url, headers, payload = _build_payload(effective_model, user, generation, system)
    logger.debug("Gemini 호출: model=%s", payload["model"])
    try:
        resp = _post_with_retry(url, headers, payload)
    except GeminiRateLimitError:
        return _hf_fallback(user, generation, system)
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
    effective_model = _resolve_model_with_state(model_id)
    url, headers, payload = _build_payload(effective_model, user, generation, system)
    logger.debug("Gemini 호출(usage): model=%s", payload["model"])
    try:
        resp = _post_with_retry(url, headers, payload)
    except GeminiRateLimitError:
        text = _hf_fallback(user, generation, system)
        return text, {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
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
