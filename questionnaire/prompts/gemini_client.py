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
_DEFAULT_MODEL = "gemini-2.5-flash"

_QUOTA_ERROR_MSG = (
    "[Gemini 한도 초과] 분당 요청 한도(RPM)를 초과했습니다. "
    "잠시 후 다시 시도해 주세요. "
    "반복적으로 발생하면 Google AI Studio에서 사용량을 확인하세요."
)


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


def _post(url: str, headers: dict, payload: dict, max_retries: int = 3) -> requests.Response:
    """Gemini API 호출. 5xx 에러는 최대 3회 재시도, 429는 즉시 RuntimeError."""
    for attempt in range(max_retries + 1):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=60)
            if resp.status_code == 429:
                logger.warning("Gemini 429 한도 초과 (model=%s)", payload.get("model"))
                raise RuntimeError(_QUOTA_ERROR_MSG)
            if resp.status_code >= 500:
                if attempt < max_retries:
                    wait = 2 ** attempt
                    logger.warning("Gemini %d 서버 오류 — %d초 후 재시도 (%d/%d)",
                                   resp.status_code, wait, attempt + 1, max_retries)
                    time.sleep(wait)
                    continue
                raise requests.HTTPError(response=resp)
            resp.raise_for_status()
            return resp
        except RuntimeError:
            raise
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else None
            if code in (401, 403):
                raise RuntimeError(
                    f"Gemini API 인증 실패({code}). GEMINI_API_KEY 값을 확인하세요."
                ) from e
            if code == 404:
                raise RuntimeError(
                    "Gemini 모델을 찾을 수 없습니다(404). "
                    "GEMINI_MODEL_ID 환경 변수로 올바른 모델명을 지정하세요."
                ) from e
            raise RuntimeError(f"Gemini API 오류({code}): {e}") from e
        except requests.RequestException as e:
            if attempt < max_retries:
                wait = 2 ** attempt
                logger.warning("Gemini 네트워크 오류 — %d초 후 재시도 (%d/%d): %s",
                               wait, attempt + 1, max_retries, e)
                time.sleep(wait)
                continue
            raise RuntimeError(f"Gemini 네트워크 오류: {e}") from e
    raise RuntimeError("Gemini API 재시도 한도 초과")


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


def chat_completion_generate(
    model_id: str,
    user: str,
    generation: dict[str, Any],
    *,
    system: str | None = None,
) -> str:
    url, headers, payload = _build_payload(model_id, user, generation, system)
    logger.debug("Gemini 호출: model=%s", payload["model"])
    resp = _post(url, headers, payload)
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
    url, headers, payload = _build_payload(model_id, user, generation, system)
    logger.debug("Gemini 호출(usage): model=%s", payload["model"])
    resp = _post(url, headers, payload)
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


_GEMINI_NATIVE_BASE = "https://generativelanguage.googleapis.com/v1beta"


def _native_headers() -> dict:
    return {
        "x-goog-api-key": _api_key(),
        "Content-Type": "application/json",
    }


def generate_with_context_cache(
    model_id: str,
    user: str,
    generation: dict[str, Any],
    *,
    system: str,
) -> tuple[str, dict]:
    """
    Gemini Native Context Caching API 사용.
    system prompt를 캐시로 등록 후 생성 → 실측 캐시/신규 토큰 반환.
    캐시 생성 실패(토큰 미달 등) 시 일반 방식으로 폴백.
    반환 usage: {input_tokens, output_tokens, cached_tokens, fresh_tokens, cache_supported}
    """
    model = _model_id(model_id)
    native_model = f"models/{model}" if not model.startswith("models/") else model
    headers = _native_headers()

    # ── 1. 캐시 생성 ──────────────────────────────────────────
    cache_name = None
    cache_token_count = 0
    cache_error = None
    try:
        cache_payload = {
            "model": native_model,
            "systemInstruction": {"parts": [{"text": system.strip()}]},
            "ttl": "300s",
        }
        cache_resp = requests.post(
            f"{_GEMINI_NATIVE_BASE}/cachedContents",
            headers=headers,
            json=cache_payload,
            timeout=30,
        )
        if not cache_resp.ok:
            api_err = cache_resp.json()
            err_msg = (api_err.get("error") or {}).get("message") or cache_resp.text[:200]
            cache_error = f"캐시 API 오류 ({cache_resp.status_code}): {err_msg}"
            logger.warning("Gemini 캐시 생성 실패 — 폴백: %s", cache_error)
        else:
            cache_data = cache_resp.json()
            cache_name = cache_data.get("name")
            cache_token_count = (cache_data.get("usageMetadata") or {}).get("totalTokenCount", 0)
            logger.debug("Gemini 캐시 생성: name=%s tokens=%d", cache_name, cache_token_count)
    except Exception as e:
        cache_error = str(e)
        logger.warning("Gemini 캐시 생성 실패 — 폴백: %s", e)

    # ── 2. 생성 ───────────────────────────────────────────────
    try:
        if cache_name:
            gen_payload = {
                "cachedContent": cache_name,
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": {
                    "maxOutputTokens": int(generation.get("max_tokens", 3000)),
                    "temperature": float(generation.get("temperature", 0.7)),
                },
            }
            gen_resp = requests.post(
                f"{_GEMINI_NATIVE_BASE}/{native_model}:generateContent",
                headers=headers,
                json=gen_payload,
                timeout=120,
            )
            gen_resp.raise_for_status()
            gen_data = gen_resp.json()

            try:
                content = gen_data["candidates"][0]["content"]["parts"][0]["text"]
            except (KeyError, IndexError, TypeError) as e:
                raise TypeError(f"Gemini Native 응답 형식 오류: {json.dumps(gen_data)[:300]}") from e

            meta = gen_data.get("usageMetadata") or {}
            total_in = int(meta.get("promptTokenCount", 0))
            cached = int(meta.get("cachedContentTokenCount", 0))
            out = int(meta.get("candidatesTokenCount", 0))
            usage = {
                "input_tokens": total_in,
                "output_tokens": out,
                "cached_tokens": cached,
                "fresh_tokens": total_in - cached,
                "cache_supported": True,
            }
            return (content or "").strip(), usage

        else:
            # 캐시 없이 일반 방식
            result, usage = chat_completion_generate_with_usage(model_id, user, generation, system=system)
            usage["cached_tokens"] = 0
            usage["fresh_tokens"] = usage["input_tokens"]
            usage["cache_supported"] = False
            usage["cache_error"] = cache_error or "unknown"
            return result, usage

    finally:
        # ── 3. 캐시 삭제 ──────────────────────────────────────
        if cache_name:
            try:
                requests.delete(
                    f"{_GEMINI_NATIVE_BASE}/{cache_name}",
                    headers=headers,
                    timeout=10,
                )
                logger.debug("Gemini 캐시 삭제: %s", cache_name)
            except Exception as e:
                logger.warning("Gemini 캐시 삭제 실패(무시): %s", e)
