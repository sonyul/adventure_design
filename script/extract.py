"""본문 추출 (08 ADR-009 `extract.py`, FR-02-2, A3).

실패 기준: ① 열지 못함(오류·10초 초과) ② 200자 미만 ③ 빈 값. 기사당 3,000자까지만 쓴다.
추출한 본문은 메모리에서만 쓰고 파일에 저장하지 않는다 (NFR-08).
"""
from __future__ import annotations

import requests
import trafilatura

import config

_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"),
    "Accept-Language": "ko-KR,ko;q=0.9",
}


def extract_text(url: str) -> tuple[str, str]:
    """(본문, 결과 코드). 결과 코드는 06 4-7: ok / open_failed / too_short / empty."""
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=config.EXTRACT_TIMEOUT_SEC)
        resp.raise_for_status()
    except requests.RequestException:
        return "", "open_failed"
    # 한국 언론사 중 euc-kr 페이지가 있어 글자 깨짐을 막기 위해 바이트 그대로 넘긴다
    try:
        text = trafilatura.extract(resp.content, url=url, include_comments=False,
                                   include_tables=False, favor_precision=True)
    except Exception:
        text = None
    if not text or not text.strip():
        return "", "empty"
    text = text.strip()
    if len(text) < config.EXTRACT_MIN_CHARS:
        return "", "too_short"
    return text[: config.EXTRACT_MAX_CHARS], "ok"
