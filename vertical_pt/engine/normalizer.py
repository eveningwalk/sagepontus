"""
Normalizer — 비정형 텍스트 전처리 레이어
다양한 입력 소스의 노이즈를 제거하고 임상 본문만 반환한다.

지원 소스:
  - mtsamples  : HTML 스크랩 (disclaimer, Related Samples 등)
  - webpt      : WebPT EMR DOM (환자 헤더, 네비게이션 잔재)
  - raw        : 노이즈 없는 순수 텍스트 (패스스루)

파이프라인:
  raw input
    → _decode_entities      (HTML 엔티티 / \xa0 제거)
    → _strip_front          (소스별 앞단 boilerplate)
    → _strip_tail           (소스별 뒷단 노이즈)
    → _normalize_whitespace (연속 공백/빈줄 정리)
    → _tag_soap_sections    (선택) SOAP 섹션 헤더 정규화
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

Source = Literal["mtsamples", "webpt", "raw"]

_SECTION_NAMES: frozenset[str] = frozenset({"SUBJECTIVE", "OBJECTIVE", "ASSESSMENT", "PLAN"})

# ── SOAP 섹션 헤더 정규화 매핑 ────────────────────────────────────────────────
_SOAP_HEADER_MAP: dict[str, str] = {
    # Subjective
    r"\bsubjective\b":          "SUBJECTIVE",
    r"\bchief\s+complaint\b":   "SUBJECTIVE",
    r"\bcc\b":                  "SUBJECTIVE",
    r"\bhistory\b":             "SUBJECTIVE",
    r"\bhpi\b":                 "SUBJECTIVE",
    # Objective
    r"\bobjective\b":           "OBJECTIVE",
    r"\bphysical\s+exam(?:ination)?\b": "OBJECTIVE",
    r"\bexamination\b":         "OBJECTIVE",
    r"\bfindings\b":            "OBJECTIVE",
    # Assessment
    r"\bassessment\b":          "ASSESSMENT",
    r"\bdiagnosis\b":           "ASSESSMENT",
    r"\bimpression\b":          "ASSESSMENT",
    # Plan
    r"\bplan\b":                "PLAN",
    r"\btreatment\b":           "PLAN",
    r"\btherapeutic\s+interventions?\b": "PLAN",
    r"\brecommendations?\b":    "PLAN",
    r"\bdisposition\b":         "PLAN",
}

# 섹션 헤더 패턴: 줄 시작 + 키워드 + 콜론/줄끝
_SECTION_RE = re.compile(
    r"^(" + "|".join(_SOAP_HEADER_MAP.keys()) + r")[ \t]*:?[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)

# ── 소스별 앞단 boilerplate 컷오프 패턴 ───────────────────────────────────────
# 이 패턴 직전까지 제거. 패턴 자체는 보존 or 제거 여부는 _strip_front에서 결정.
_FRONT_CUT: dict[Source, list[re.Pattern]] = {
    "mtsamples": [
        # "Description:\n<실제 요약>" 이후부터 임상 내용
        re.compile(r"^Description:\s*\n", re.IGNORECASE | re.MULTILINE),
        # fallback: 첫 SOAP 섹션 헤더
        _SECTION_RE,
    ],
    "webpt": [
        # WebPT 노트 본문은 "Visit Note" 또는 "SOAP Note" 이후
        re.compile(r"^(?:Visit\s+Note|SOAP\s+Note|Progress\s+Note)\s*\n",
                   re.IGNORECASE | re.MULTILINE),
        _SECTION_RE,
    ],
    "raw": [],
}

# ── 소스별 뒷단 노이즈 컷오프 패턴 ───────────────────────────────────────────
_TAIL_CUT: dict[Source, list[re.Pattern]] = {
    "mtsamples": [
        re.compile(r"\bThis is not medical advice\b", re.IGNORECASE),
        re.compile(r"\bGo Back to\b", re.IGNORECASE),
        re.compile(r"\bRelated Samples\b", re.IGNORECASE),
        re.compile(r"^Keywords?:\s*", re.IGNORECASE | re.MULTILINE),
    ],
    "webpt": [
        re.compile(r"\bSave\b.*\bCancel\b", re.IGNORECASE),
        re.compile(r"^(?:Home|Dashboard|Patients|Schedule)\s*$",
                   re.IGNORECASE | re.MULTILINE),
    ],
    "raw": [],
}


# ── 내부 유틸 ─────────────────────────────────────────────────────────────────

def _decode_entities(text: str) -> str:
    """HTML 엔티티, \xa0(non-breaking space), zero-width 문자 제거."""
    text = text.replace("\xa0", " ")
    text = text.replace("​", "").replace("‌", "").replace("‍", "")
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&#\d+;", " ", text)
    return text


def _strip_front(text: str, source: Source) -> str:
    """앞단 boilerplate를 첫 번째 매칭 패턴 위치에서 잘라낸다."""
    for pattern in _FRONT_CUT.get(source, []):
        m = pattern.search(text)
        if m:
            # 패턴 자체(Description: 헤더 등)는 제거, 내용부터 보존
            text = text[m.end():]
            break
    return text


def _strip_tail(text: str, source: Source) -> str:
    """뒷단 노이즈를 첫 번째 매칭 패턴 위치에서 잘라낸다."""
    earliest = len(text)
    for pattern in _TAIL_CUT.get(source, []):
        m = pattern.search(text)
        if m and m.start() < earliest:
            earliest = m.start()
    return text[:earliest]


_INLINE_NOISE: list[re.Pattern] = [
    # "(Medical Transcription Sample Report)" 블록
    re.compile(r"\(Medical Transcription Sample Report\)", re.IGNORECASE),
    # "Intended for: ... practicing clinical documentation formats in XYZ." 블록
    re.compile(
        r"Intended for:.*?(?:documentation formats in [^\n]+\.)\s*",
        re.IGNORECASE | re.DOTALL,
    ),
]


def _strip_inline_noise(text: str) -> str:
    """본문 중간에 박혀있는 boilerplate 블록 제거."""
    for pattern in _INLINE_NOISE:
        text = pattern.sub("", text)
    return text


def _normalize_whitespace(text: str) -> str:
    """탭→스페이스, 줄 끝 공백 제거, 3줄 이상 빈줄 → 2줄로 압축."""
    text = text.replace("\t", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _tag_soap_sections(text: str) -> str:
    """SOAP 섹션 헤더를 대문자 표준 형식으로 정규화."""
    def replace_header(m: re.Match) -> str:
        raw = m.group(0).strip().rstrip(":").lower()
        for pattern, label in _SOAP_HEADER_MAP.items():
            if re.fullmatch(pattern, raw, re.IGNORECASE):
                return f"\n{label}:"
        return m.group(0)

    return _SECTION_RE.sub(replace_header, text)


# ── 공개 API ──────────────────────────────────────────────────────────────────

@dataclass
class NormalizeResult:
    text: str
    source: Source
    original_len: int
    cleaned_len: int
    reduction_pct: float = field(init=False)

    def __post_init__(self) -> None:
        self.reduction_pct = round(
            (1 - self.cleaned_len / self.original_len) * 100, 1
        ) if self.original_len else 0.0


def normalize(text: str, source: Source = "raw", tag_sections: bool = True) -> NormalizeResult:
    """
    비정형 텍스트를 임상 본문으로 정제한다.

    Args:
        text:         원본 텍스트
        source:       입력 소스 ("mtsamples" | "webpt" | "raw")
        tag_sections: True이면 SOAP 섹션 헤더를 대문자로 정규화

    Returns:
        NormalizeResult.text — 정제된 임상 텍스트
    """
    original_len = len(text)

    text = _decode_entities(text)
    text = _strip_front(text, source)
    text = _strip_inline_noise(text)
    text = _strip_tail(text, source)
    text = _normalize_whitespace(text)
    if tag_sections:
        text = _tag_soap_sections(text)

    return NormalizeResult(
        text=text,
        source=source,
        original_len=original_len,
        cleaned_len=len(text),
    )


def normalize_batch(
    texts: list[str],
    source: Source = "raw",
    tag_sections: bool = True,
) -> list[NormalizeResult]:
    return [normalize(t, source, tag_sections) for t in texts]


def split_sections(text: str) -> dict[str, str]:
    """
    태깅된 SOAP 텍스트를 섹션별로 분리.
    normalize(..., tag_sections=True) 결과에 적용.

    Returns:
        {"SUBJECTIVE": "...", "OBJECTIVE": "...", "ASSESSMENT": "...",
         "PLAN": "...", "UNKNOWN": "..."}
    """
    buckets: dict[str, list[str]] = {s: [] for s in _SECTION_NAMES}
    buckets["UNKNOWN"] = []
    current = "UNKNOWN"

    for line in text.splitlines():
        stripped = line.strip()
        candidate = stripped.rstrip(":")
        if stripped.endswith(":") and candidate in _SECTION_NAMES:
            current = candidate
        else:
            buckets[current].append(line)

    return {k: "\n".join(v).strip() for k, v in buckets.items()}
