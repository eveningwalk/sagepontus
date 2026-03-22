"""접속 단말 구분(서버 사이드). User-Agent + Client Hints(가능 시)."""
from __future__ import annotations

import re

# 태블릿·폰 등 좁은 화면용 레이아웃에 사용
_MOBILE_UA_RE = re.compile(
    r"(?:Mobile|Android|iPhone|iPod|webOS|BlackBerry|IEMobile|Opera Mini|"
    r"Tablet|iPad|Silk|Kindle)",
    re.IGNORECASE,
)


def is_mobile_request(request) -> bool:
    """
    모바일·태블릿 등 터치 우선 레이아웃을 쓸지 여부.
    Sec-CH-UA-Mobile 이 있으면 우선(Chrome 계열).
    """
    ch = request.META.get("HTTP_SEC_CH_UA_MOBILE")
    if ch == "?1":
        return True
    if ch == "?0":
        return False
    ua = request.META.get("HTTP_USER_AGENT") or ""
    if not ua.strip():
        return False
    if _MOBILE_UA_RE.search(ua):
        return True
    # iPadOS 13+ Safari 는 Macintosh 로 위장하는 경우가 있음
    if "Macintosh" in ua and "Safari" in ua and "Chrome" not in ua:
        if "Mobile" in ua or request.META.get("HTTP_SEC_CH_UA_PLATFORM") == '"iOS"':
            return True
    return False


def landing_template_name(request) -> str:
    """데모 랜딩: 모바일 UA → 전용 템플릿."""
    if is_mobile_request(request):
        return "questionnaire/landing_mobile.html"
    return "questionnaire/landing.html"
