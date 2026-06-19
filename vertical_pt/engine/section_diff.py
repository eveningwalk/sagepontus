"""
Section-level diff for PT clinical documents.

PT 문서는 ALL-CAPS 헤더(e.g. PATIENT PROFILE:) 로 섹션을 구분한다.
원본과 수정본을 섹션 단위로 비교해 어느 섹션이 바뀌었는지 기록한다.
"""

from __future__ import annotations
import re

_HEADER_RE = re.compile(r'^([A-Z][A-Z0-9 \-/]{1,}):[ \t]*$', re.MULTILINE)


def _parse_sections(text: str) -> dict[str, str]:
    """텍스트를 섹션 헤더 기준으로 분리 → {헤더: 내용} dict."""
    headers = list(_HEADER_RE.finditer(text))
    if not headers:
        return {"(BODY)": text.strip()}

    sections: dict[str, str] = {}
    for i, m in enumerate(headers):
        key = m.group(1).strip()
        start = m.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        sections[key] = text[start:end].strip()
    return sections


def compute_section_diffs(original: str, edited: str) -> list[dict]:
    """
    두 문서를 섹션 단위로 비교.

    반환값: [
        {"section": "PATIENT PROFILE", "status": "modified",
         "original": "...", "edited": "..."},
        {"section": "CLINICAL FINDINGS", "status": "unchanged", ...},
        {"section": "NEW SECTION", "status": "added", "original": "", "edited": "..."},
    ]
    status: unchanged | modified | added | removed
    """
    orig_secs = _parse_sections(original)
    edit_secs = _parse_sections(edited)
    all_keys = list(orig_secs.keys()) + [k for k in edit_secs if k not in orig_secs]

    result = []
    for key in all_keys:
        o = orig_secs.get(key, "")
        e = edit_secs.get(key, "")
        if o == e:
            status = "unchanged"
        elif not o:
            status = "added"
        elif not e:
            status = "removed"
        else:
            status = "modified"
        result.append({"section": key, "status": status, "original": o, "edited": e})
    return result
