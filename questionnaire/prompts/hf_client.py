"""Hugging Face Inference API(chat) 호출."""

from __future__ import annotations

import logging
import os
from typing import Any

from requests import HTTPError

logger = logging.getLogger(__name__)

_HF_TOKEN_HELP = (
    "https://huggingface.co/settings/tokens 에서 읽기(read) 토큰을 발급하고 "
    "환경 변수 HF_TOKEN 또는 HUGGINGFACE_HUB_TOKEN 에 설정하세요. "
    "(router.huggingface.co Inference 호출에는 로그인 토큰이 필요합니다.)"
)


def _inference_provider() -> str:
    """
    Hub가 모델별 Inference Provider를 고릅니다(기본 auto).
    hf-inference만 쓰면 Router에 배포되지 않은 모델은 404. 매핑이 비어 있으면 StopIteration.
    HF_INFERENCE_PROVIDER=hf-inference 로 고정 가능.
    """
    raw = (os.environ.get("HF_INFERENCE_PROVIDER") or "").strip()
    if not raw:
        return "auto"
    return raw


def chat_completion_generate(model_id: str, system: str, user: str, generation: dict[str, Any]) -> str:
    """
    InferenceClient.chat_completion — OpenAI 호환 응답에서 본문만 반환.
    토큰: HF_TOKEN 또는 HUGGINGFACE_HUB_TOKEN.
    Router 호출에는 보통 유효한 Hub 토큰이 필요(401 방지).
    라우팅: HF_INFERENCE_PROVIDER (기본 auto; hf-inference 는 해당 라우트에만·미배포 모델은 404).
    """
    try:
        from huggingface_hub import InferenceClient
    except ImportError as e:
        raise RuntimeError(
            "huggingface_hub 패키지가 필요합니다. requirements.txt에 huggingface-hub를 추가하고 설치하세요."
        ) from e

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN") or None
    client = InferenceClient(model=model_id, token=token, provider=_inference_provider())

    kwargs: dict[str, Any] = {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": int(generation.get("max_tokens", 512)),
        "temperature": float(generation.get("temperature", 0.7)),
    }
    top_p = generation.get("top_p")
    if top_p is not None:
        kwargs["top_p"] = float(top_p)

    try:
        response = client.chat_completion(**kwargs)
    except Exception as e:
        resp = getattr(e, "response", None)
        code = getattr(resp, "status_code", None) if resp is not None else None
        if code == 401:
            raise RuntimeError(f"Hugging Face Inference 인증 실패(401). {_HF_TOKEN_HELP}") from e
        if code == 404:
            raise RuntimeError(
                "Hugging Face Inference에서 해당 모델·엔드포인트를 찾을 수 없습니다(404). "
                "모델 카드에 Inference Provider가 없으면 Router에 배포되지 않습니다. "
                "manifest 기본은 Qwen2.5 Instruct 계열이며, HF_MODEL_ID 로 다른 Instruct 모델을 지정할 수 있습니다."
            ) from e
        if isinstance(e, HTTPError):
            raise
        raise

    if hasattr(response, "choices") and response.choices:
        content = response.choices[0].message.content
    elif isinstance(response, dict) and response.get("choices"):
        content = response["choices"][0].get("message", {}).get("content")
    else:
        raise TypeError(f"예상하지 못한 chat_completion 응답 형식: {type(response)!r}")
    if content is None:
        return ""
    return content.strip()
