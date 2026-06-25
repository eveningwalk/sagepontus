"""RAG retrieval engine.

RAG-1: MCID lookup — structured JSON KB, no embeddings needed.
RAG-2: APTA CPG semantic search — Gemini gemini-embedding-001 + cosine similarity.
"""
from __future__ import annotations

import json
import logging
import math
import os
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

_MCID_KB_PATH = Path(__file__).resolve().parents[2] / "data" / "mcid_kb.json"
_mcid_kb: list[dict] | None = None


# ── MCID KB loader ────────────────────────────────────────────────────────────

def _load_mcid_kb() -> list[dict]:
    global _mcid_kb
    if _mcid_kb is None:
        with open(_MCID_KB_PATH, encoding="utf-8") as f:
            _mcid_kb = json.load(f)["measures"]
    return _mcid_kb


# ── RAG-1: MCID lookup ────────────────────────────────────────────────────────

def get_mcid_context(soap_text: str) -> str:
    """Scan SOAP text for known outcome measure names → return MCID citation block."""
    measures = _load_mcid_kb()
    soap_lower = soap_text.lower()
    found = []

    for m in measures:
        if any(name in soap_lower for name in m["names"]):
            found.append(m)

    if not found:
        return ""

    lines = ["[MCID Reference — for documentation only, do not fabricate scores]"]
    for m in found:
        lines.append(
            f"- {m['full_name']}: MCID = {m['mcid']} {m['unit']} "
            f"({m['direction']}). {m['context']} (Source: {m['source']})"
        )
    return "\n".join(lines)


# ── Gemini Embedding ──────────────────────────────────────────────────────────

def _embed(text: str) -> list[float]:
    """Call Gemini gemini-embedding-001 and return float list."""
    import requests

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    url = (
        f"https://generativelanguage.googleapis.com/v1/"
        f"models/gemini-embedding-001:embedContent?key={api_key}"
    )
    # gemini-embedding-001 limit: 2048 tokens (~1500 chars safe margin)
    payload = {
        "content": {"parts": [{"text": text[:1500]}]},
        "taskType": "RETRIEVAL_DOCUMENT",
    }
    resp = requests.post(url, json=payload, timeout=30)
    if not resp.ok:
        raise RuntimeError(f"Embedding API {resp.status_code}: {resp.text[:200]}")
    return resp.json()["embedding"]["values"]


def embed_text(text: str) -> list[float]:
    """Public wrapper — returns [] on error so callers can degrade gracefully."""
    try:
        return _embed(text)
    except Exception as e:
        logger.warning("Embedding failed: %s", e)
        return []


# ── Cosine similarity ─────────────────────────────────────────────────────────

def _cosine(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a, dtype=np.float32), np.array(b, dtype=np.float32)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(np.dot(va, vb) / denom) if denom > 0 else 0.0


# ── RAG-2: APTA CPG retrieval ─────────────────────────────────────────────────

def retrieve_cpg(
    query: str,
    condition: str = "",
    top_k: int = 3,
) -> str:
    """Retrieve relevant APTA CPG chunks for a query.

    Returns a formatted citation block ready for prompt injection.
    Falls back to keyword pre-filter if embedding is unavailable.
    """
    from vertical_pt.models import KnowledgeChunk

    qs = KnowledgeChunk.objects.filter(source="apta_cpg")
    if condition:
        cond_lower = condition.lower()
        cond_qs = qs.filter(condition__icontains=cond_lower)
        if cond_qs.exists():
            qs = cond_qs

    chunks = list(qs.only("title", "content", "embedding", "meta"))
    if not chunks:
        return ""

    query_vec = embed_text(query)

    if query_vec:
        scored = [
            (c, _cosine(query_vec, c.embedding))
            for c in chunks if c.embedding
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        top = [c for c, _ in scored[:top_k]]
    else:
        # fallback: keyword match
        q_lower = query.lower()
        top = [c for c in chunks if any(w in c.content.lower() for w in q_lower.split())][:top_k]
        if not top:
            top = chunks[:top_k]

    if not top:
        return ""

    lines = ["[APTA Clinical Practice Guideline — cite source in letter]"]
    for c in top:
        url = c.meta.get("url", "")
        ref = f" ({url})" if url else ""
        lines.append(f"\n[{c.title}{ref}]\n{c.content}")
    return "\n".join(lines)
