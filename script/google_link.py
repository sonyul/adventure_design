"""구글 뉴스 링크 -> 원문 주소 바꾸기 (08 ADR-007 `google_link.py`, 제약 C4).

googlenewsdecoder 부품을 쓴다. 실패하면 원래 구글 링크를 그대로 돌려준다 (ADR-007 확정).
"""
from __future__ import annotations

from googlenewsdecoder import gnewsdecoder

import config


def decode(url: str) -> tuple[str, bool]:
    """(바꾼 주소, 성공 여부). 실패하면 (원래 주소, False)."""
    try:
        res = gnewsdecoder(url, interval=config.GOOGLE_DECODE_INTERVAL_SEC,
                           timeout=config.HTTP_TIMEOUT_SEC)
    except Exception:  # 부품 내부 오류도 실패로만 본다 (NFR-10)
        return url, False
    # googlenewsdecoder 0.2.2 응답: {"success": true, "decoded_url": "..."} (실측 2026-10-28)
    # 옛 버전은 "status" 키를 썼으므로 둘 다 받아 준다.
    if isinstance(res, dict) and (res.get("success") or res.get("status")) and res.get("decoded_url"):
        return str(res["decoded_url"]), True
    return url, False
