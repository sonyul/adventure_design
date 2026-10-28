"""기사 모으기 (08 ADR-009 `collect.py`) - A1 구글 뉴스 RSS, A2 네이버 뉴스 검색.

FR-01-4 오늘의 화제, FR-01-5 나의 관심 분야, FR-01-9 다른 분야 한 줄(검색 부분).
여기서는 제목·링크·언론사·날짜·요약만 다룬다. 본문은 extract.py 담당.
"""
from __future__ import annotations

import html
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import urlparse

import feedparser
import requests

import config

KST = timezone(timedelta(hours=9))


@dataclass
class RawArticle:
    """원문 기사 1개 (D5 출처의 재료)."""
    title: str
    url: str                      # 지금 쓰는 링크 (구글 경유 or 원문 or 네이버)
    link_type: str                # original / google / naver (06 4-5)
    press: str | None = None
    published_at: datetime | None = None
    summary: str = ""             # 네이버 description (태그 제거). 구글은 비어 있음
    # 처리 중에만 쓰는 값 (저장하지 않음)
    text: str = field(default="", repr=False)   # 추출한 본문 - 절대 파일에 저장하지 않는다 (NFR-08)
    extract_result: str = "not_tried"          # 06 4-7
    decode_tried: bool = False


@dataclass
class Group:
    """같은 사건 기사 묶음 (FR-02-1)."""
    page: str                     # today / interest / recommend
    topic: str
    articles: list[RawArticle]


# ---------------- A1 구글 뉴스 RSS ----------------
class _ListParser(HTMLParser):
    """RSS description 안의 <ol><li><a href>제목</a> <font>언론사</font></li></ol> 읽기."""

    def __init__(self) -> None:
        super().__init__()
        self.items: list[dict] = []
        self._cur: dict | None = None
        self._in_a = False
        self._in_font = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "li":
            self._cur = {"url": "", "title": "", "press": ""}
        elif tag == "a" and self._cur is not None:
            self._cur["url"] = a.get("href", "")
            self._in_a = True
        elif tag == "font" and self._cur is not None:
            self._in_font = True

    def handle_endtag(self, tag):
        if tag == "a":
            self._in_a = False
        elif tag == "font":
            self._in_font = False
        elif tag == "li" and self._cur is not None:
            if self._cur["url"] and self._cur["title"]:
                self.items.append({k: v.strip() for k, v in self._cur.items()})
            self._cur = None

    def handle_data(self, data):
        if self._cur is None:
            return
        if self._in_a:
            self._cur["title"] += data
        elif self._in_font:
            self._cur["press"] += data


def _strip_press_suffix(title: str, press: str | None) -> str:
    if press and title.endswith(" - " + press):
        return title[: -(len(press) + 3)].strip()
    return title.strip()


def fetch_google_top(limit: int = config.CANDIDATE_GROUPS) -> list[Group]:
    """구글 뉴스 '주요 뉴스' RSS 위에서 limit개 묶음. 실패하면 예외 (호출한 쪽이 PAGE_SKIPPED 처리)."""
    resp = requests.get(config.GOOGLE_RSS_URL, timeout=config.HTTP_TIMEOUT_SEC,
                        headers={"User-Agent": "Mozilla/5.0 (news-bwa trial)"})
    resp.raise_for_status()
    feed = feedparser.parse(resp.content)
    if not feed.entries:
        raise RuntimeError("구글 뉴스 RSS가 비어 있음")
    groups: list[Group] = []
    for entry in feed.entries[:limit]:
        src = entry.get("source") or {}
        press = src.get("title") if isinstance(src, dict) else None
        pub = None
        if entry.get("published"):
            try:
                pub = parsedate_to_datetime(entry.published).astimezone(KST)
            except (TypeError, ValueError):
                pub = None
        parser = _ListParser()
        parser.feed(entry.get("summary", ""))
        members = parser.items
        articles: list[RawArticle] = []
        if members:
            for i, m in enumerate(members[: config.MAX_ARTICLES_PER_GROUP]):
                articles.append(RawArticle(
                    title=html.unescape(m["title"]), url=m["url"], link_type="google",
                    press=m["press"] or None, published_at=pub if i == 0 else None))
        else:  # 목록이 없으면 대표 기사 1개만
            articles.append(RawArticle(
                title=_strip_press_suffix(entry.title, press), url=entry.link,
                link_type="google", press=press, published_at=pub))
        groups.append(Group(page="today", topic=_strip_press_suffix(entry.title, press),
                            articles=articles))
    return groups


# ---------------- A2 네이버 뉴스 검색 ----------------
_TAG_RE = re.compile(r"<[^>]+>")


def clean_naver_text(s: str) -> str:
    """<b> 태그와 &quot; 같은 글자 표시를 없앤다."""
    return html.unescape(_TAG_RE.sub("", s or "")).strip()


def naver_keys() -> tuple[str, str] | None:
    cid = os.environ.get("NAVER_CLIENT_ID", "").strip()
    sec = os.environ.get("NAVER_CLIENT_SECRET", "").strip()
    return (cid, sec) if cid and sec else None


def naver_search(keyword: str, display: int = config.NAVER_DISPLAY) -> list[RawArticle]:
    """네이버 뉴스 검색 1회 (최신순). 키 오류·한도 초과 등은 예외."""
    keys = naver_keys()
    if keys is None:
        raise RuntimeError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수가 없음")
    resp = requests.get(
        config.NAVER_URL,
        params={"query": keyword, "display": display, "start": 1, "sort": "date"},
        headers={"X-Naver-Client-Id": keys[0], "X-Naver-Client-Secret": keys[1]},
        timeout=config.HTTP_TIMEOUT_SEC,
    )
    if resp.status_code != 200:
        # 응답 본문의 errorCode만 남긴다 (키 값은 응답에 없음)
        try:
            code = resp.json().get("errorCode", "")
        except ValueError:
            code = ""
        raise RuntimeError(f"네이버 API 오류 HTTP {resp.status_code} {code}".strip())
    out: list[RawArticle] = []
    for it in resp.json().get("items", []):
        original = (it.get("originallink") or "").strip()
        naver = (it.get("link") or "").strip()
        url, ltype = (original, "original") if original else (naver, "naver")
        if not url:
            continue
        try:
            pub = parsedate_to_datetime(it.get("pubDate", "")).astimezone(KST)
        except (TypeError, ValueError):
            pub = None
        out.append(RawArticle(
            title=clean_naver_text(it.get("title", "")), url=url, link_type=ltype,
            press=press_from_url(url), published_at=pub,
            summary=clean_naver_text(it.get("description", ""))))
    return out


def press_from_url(url: str) -> str | None:
    """네이버 응답에는 언론사 항목이 없다 -> 원문 주소의 사이트 이름(도메인)으로 대신 (07 2-2 결정)."""
    host = urlparse(url).hostname or ""
    host = host.removeprefix("www.").removeprefix("m.")
    return host or None


def collect_naver(keywords: list[str], now: datetime | None = None) -> tuple[list[RawArticle], bool]:
    """키워드들로 검색 -> 24시간(부족하면 48시간) 필터 -> 같은 링크 중복 제거.
    돌려주는 값: (기사 목록 최신순, 48시간으로 늘렸는지)."""
    now = now or datetime.now(KST)
    pool: list[RawArticle] = []
    for kw in keywords:
        pool.extend(naver_search(kw))
    widened = False
    picked = _filter_window(pool, now, config.WINDOW_HOURS)
    if not picked:
        widened = True
        picked = _filter_window(pool, now, config.WINDOW_HOURS_WIDE)
    return picked, widened


def _filter_window(pool: list[RawArticle], now: datetime, hours: int) -> list[RawArticle]:
    seen: set[str] = set()
    out: list[RawArticle] = []
    for a in sorted(pool, key=lambda x: x.published_at or datetime.min.replace(tzinfo=KST), reverse=True):
        if a.published_at is None or now - a.published_at > timedelta(hours=hours):
            continue
        if a.url in seen:
            continue
        seen.add(a.url)
        out.append(a)
    return out
