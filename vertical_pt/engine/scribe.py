"""
Audio Scribe Integration — PT Red Flag Service

현재: AssemblyAI Medical API
ScribePT 승인 후: SCRIBE_PT_MODE = True 로 변경
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ─── 설정 ────────────────────────────────────────────────────────────────────
SCRIBE_PT_MODE = os.getenv("SCRIBE_PT_MODE", "").lower() in ("1", "true", "yes")

ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY", "")
SCRIBEPT_API_KEY   = os.getenv("SCRIBEPT_API_KEY", "")

ASSEMBLYAI_UPLOAD_URL     = "https://api.assemblyai.com/v2/upload"
ASSEMBLYAI_TRANSCRIPT_URL = "https://api.assemblyai.com/v2/transcript"

# ScribePT 승인 후 실제 endpoint로 교체
SCRIBEPT_UPLOAD_URL     = "https://api.scribept.com/v1/upload"
SCRIBEPT_TRANSCRIPT_URL = "https://api.scribept.com/v1/transcript"


# ─── AssemblyAI 구현 ──────────────────────────────────────────────────────────
async def _transcribe_assemblyai(audio_bytes: bytes) -> dict[str, Any]:
    """오디오 → 텍스트 변환 (AssemblyAI Medical). Returns: {text, utterances}"""
    if not ASSEMBLYAI_API_KEY:
        raise RuntimeError("ASSEMBLYAI_API_KEY 환경 변수가 설정되지 않았습니다.")

    headers = {"authorization": ASSEMBLYAI_API_KEY}

    async with httpx.AsyncClient(timeout=60) as client:
        # 1. 오디오 업로드
        upload_resp = await client.post(
            ASSEMBLYAI_UPLOAD_URL,
            headers=headers,
            content=audio_bytes,
        )
        upload_resp.raise_for_status()
        audio_url = upload_resp.json()["upload_url"]

        # 2. 트랜스크립트 요청 (Medical + 화자 구분)
        transcript_resp = await client.post(
            ASSEMBLYAI_TRANSCRIPT_URL,
            headers=headers,
            json={
                "audio_url": audio_url,
                "speaker_labels": True,
                "language_code": "en_us",
                "speech_model": "best",
                "domain": "medical-v1",
            },
        )
        transcript_resp.raise_for_status()
        transcript_id = transcript_resp.json()["id"]

        # 3. 완료 대기 (polling)
        for _ in range(120):  # 최대 4분
            poll = await client.get(
                f"{ASSEMBLYAI_TRANSCRIPT_URL}/{transcript_id}",
                headers=headers,
            )
            result = poll.json()
            status = result.get("status")

            if status == "completed":
                return {
                    "text": result.get("text", ""),
                    "utterances": result.get("utterances", []),
                }
            if status == "error":
                raise RuntimeError(f"AssemblyAI error: {result.get('error')}")

            await asyncio.sleep(2)

    raise RuntimeError("AssemblyAI 트랜스크립트 타임아웃")


# ─── ScribePT 구현 (승인 후 채워넣기) ─────────────────────────────────────────
async def _transcribe_scribept(audio_bytes: bytes) -> dict[str, Any]:
    """ScribePT API 연동 — 승인 후 실제 구현. AssemblyAI와 동일한 return 형식 유지."""
    if not SCRIBEPT_API_KEY:
        raise RuntimeError("SCRIBEPT_API_KEY 환경 변수가 설정되지 않았습니다.")

    headers = {"Authorization": f"Bearer {SCRIBEPT_API_KEY}"}

    async with httpx.AsyncClient(timeout=60) as client:
        # TODO: ScribePT 실제 API 문서 받은 후 구현
        upload_resp = await client.post(
            SCRIBEPT_UPLOAD_URL,
            headers=headers,
            content=audio_bytes,
        )
        upload_resp.raise_for_status()
        # ... polling 로직 동일하게 구현

    return {"text": "", "utterances": []}


# ─── 화자별 S/O 분리 ──────────────────────────────────────────────────────────
def split_soap_so(utterances: list[dict]) -> dict[str, str]:
    """
    화자별 발화를 S (환자) / O (PT 관찰) 로 분리.
    Speaker A = PT → O 재료, Speaker B = 환자 → S 재료 (AssemblyAI 기준)
    """
    pt_text: list[str]      = []
    patient_text: list[str] = []

    for u in utterances:
        speaker = u.get("speaker", "")
        text    = u.get("text", "")
        if speaker == "A":
            pt_text.append(text)
        elif speaker == "B":
            patient_text.append(text)

    return {
        "S_raw": " ".join(patient_text),
        "O_raw": " ".join(pt_text),
    }


# ─── 통합 진입점 (async) ──────────────────────────────────────────────────────
async def _process_audio_async(audio_bytes: bytes) -> dict[str, Any]:
    """오디오 → S/O 분리 + Flag 시스템 payload 구성."""
    if SCRIBE_PT_MODE:
        transcript = await _transcribe_scribept(audio_bytes)
    else:
        transcript = await _transcribe_assemblyai(audio_bytes)

    so = split_soap_so(transcript["utterances"])

    return {
        "full_text": transcript["text"],
        "S":         so["S_raw"],
        "O":         so["O_raw"],
        "provider":  "scribept" if SCRIBE_PT_MODE else "assemblyai",
    }


def process_audio(audio_bytes: bytes) -> dict[str, Any]:
    """동기 래퍼 — Django sync view에서 호출 가능."""
    return asyncio.run(_process_audio_async(audio_bytes))
