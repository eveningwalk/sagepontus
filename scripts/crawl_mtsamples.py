"""
mtsamples.com Physical Medicine & Rehab SOAP 샘플 크롤러
- 시드 URL → Related Samples BFS 탐색 → 100건 수집
출력: data/soap_samples/mtsamples_pt.json
"""

import json
import time
import re
import sys
from collections import deque
from pathlib import Path
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.mtsamples.com"
# PT 관련 카테고리 시드 URLs
SEED_URLS = [
    # Physical Medicine & Rehab (21건)
    f"{BASE_URL}/site/pages/sample.asp?Type=68-Physical+Medicine+-+Rehab&Sample=2567-Physical+Therapy+-+Outpatient+Rehab",
    # SOAP / Chart / Progress Notes
    f"{BASE_URL}/site/pages/sample.asp?Type=91-SOAP+%2F+Chart+%2F+Progress+Notes&Sample=2567-Physical+Therapy+-+Outpatient+Rehab",
    # Orthopedic
    f"{BASE_URL}/site/pages/sample.asp?Type=49-Orthopedic&Sample=1039-Knee+Arthroscopy",
    # Neurology
    f"{BASE_URL}/site/pages/sample.asp?Type=42-Neurology&Sample=865-Neurology+Consult",
    # Pain Management
    f"{BASE_URL}/site/pages/sample.asp?Type=105-Pain+Management&Sample=2100-Pain+Management+Consult",
]
OUTPUT_PATH = Path(__file__).parent.parent / "data" / "soap_samples" / "mtsamples_pt.json"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; research-bot/1.0)"}
DELAY = 1.0
MAX_SAMPLES = 100


def fetch(url: str) -> BeautifulSoup | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except requests.RequestException as e:
        print(f"  [skip] {e}", file=sys.stderr)
        return None


PT_TYPES = {"68", "91", "49", "42", "105"}  # 허용할 카테고리 Type 번호


def get_related_links(soup: BeautifulSoup) -> list[str]:
    """페이지에서 PT 관련 카테고리 Related Samples 링크 추출"""
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "sample.asp" not in href:
            continue
        # Type= 번호 추출
        m = re.search(r"[Tt]ype=(\d+)", href)
        if m and m.group(1) in PT_TYPES:
            full = href if href.startswith("http") else BASE_URL + href
            links.append(full)
    return links


def parse_sample(soup: BeautifulSoup, url: str) -> dict | None:
    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True).split("|")[0].strip() if title_tag else ""

    content_div = (
        soup.find("div", class_="mainContent")
        or soup.find("div", class_="sample_report")
        or soup.find("span", id="reportContent")
    )
    if not content_div:
        return None

    for tag in content_div.find_all(["script", "ins", "nav", "div"], class_=lambda c: c and "ad" in " ".join(c)):
        tag.decompose()

    raw = content_div.get_text(separator="\n")
    text = re.sub(r"\n{3,}", "\n\n", raw).strip()
    if len(text) < 100:
        return None

    keywords_tag = soup.find("meta", attrs={"name": "keywords"})
    keywords = keywords_tag["content"] if keywords_tag else ""

    return {"title": title, "url": url, "keywords": keywords, "text": text}


def sample_id(url: str) -> str | None:
    """URL에서 숫자 Sample ID 추출 (중복 판별용)"""
    m = re.search(r"Sample=(\d+)", url, re.IGNORECASE)
    return m.group(1) if m else None


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    visited_ids: set[str] = set()
    queue: deque[str] = deque(SEED_URLS)
    results: list[dict] = []

    print(f"시드: {len(SEED_URLS)}개 카테고리")
    print(f"목표: {MAX_SAMPLES}건\n")

    while queue and len(results) < MAX_SAMPLES:
        url = queue.popleft()

        sid = sample_id(url)
        if not sid or sid in visited_ids:
            continue
        visited_ids.add(sid)

        idx = len(results) + 1
        soup = fetch(url)
        if not soup:
            continue

        sample = parse_sample(soup, url)
        if sample:
            if any(kw in sample["title"] for kw in ("EMG", "Nerve Conduction")):
                print(f"[skip] EMG 필터: {sample['title'][:65]}")
            else:
                results.append(sample)
                print(f"[{idx}/{MAX_SAMPLES}] {sample['title'][:65]}")
        else:
            print(f"[skip] 콘텐츠 없음: {url[-50:]}")

        # Related Samples에서 미방문 링크 큐에 추가
        for link in get_related_links(soup):
            link_sid = sample_id(link)
            if link_sid and link_sid not in visited_ids:
                queue.append(link)

        time.sleep(DELAY)

    OUTPUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\n완료: {len(results)}건 → {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
