"""설정값 (08 ADR-009 `config`) - 숫자·분야 목록·AI 모델 이름을 한 곳에 모은다.

근거 문서: docs/design/03_기능명세서.md (FR-01-4~6·9, FR-02-1~4, FR-03-2), 06_데이터모델_ERD.md 4-8(분야 코드).
비밀키는 여기에 적지 않는다. 키는 환경변수에서만 읽는다 (NFR-06).
"""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = BASE_DIR / "prompts"
OUTPUT_DIR = BASE_DIR / "sample_output"

# ---- AI (A4, 07 API명세서 3장) ----
# 기본 모델: Gemini 3.1 Flash-Lite (무료 요금제 대상, ai.google.dev 확인 2026-10-28).
# 바꿀 때는 환경변수 GEMINI_MODEL 로 덮어쓴다 (NFR-09, ADR-008).
AI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
AI_TEMPERATURE = 0.7
AI_RETRY = 1                 # 실패 시 다시 시도 횟수 (FR-02-3)
AI_MIN_INTERVAL_SEC = 4.5    # 호출 사이 최소 간격. 분당 15회(RPM) 한도 가정 -> 60/15 = 4초 + 여유
AI_TIMEOUT_SEC = 60

# ---- 모으기 (A1·A2) ----
GOOGLE_RSS_URL = "https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"
CANDIDATE_GROUPS = 5         # 페이지마다 후보 묶음 수 (03 v1.4 상자)
MAX_GROUPS_PER_PAGE = 3      # 페이지마다 최대 묶음 수 (03 v1.3)
MAX_ARTICLES_PER_GROUP = 5   # 묶음당 원문 기사 수 (FR-02-1)
NAVER_URL = "https://openapi.naver.com/v1/search/news.json"
NAVER_DISPLAY = 20           # 키워드마다 최신순 20개 (FR-01-5)
NAVER_DISPLAY_OTHER = 10     # 다른 분야 한 줄: 분야마다 10개 (FR-01-9)
WINDOW_HOURS = 24            # 최근 24시간 (FR-01-5)
WINDOW_HOURS_WIDE = 48       # 부족하면 48시간 (FR-01-5 예외)
HTTP_TIMEOUT_SEC = 10

# ---- 본문 추출 (A3, FR-02-2) ----
EXTRACT_TIMEOUT_SEC = 10
EXTRACT_MIN_CHARS = 200
EXTRACT_MAX_CHARS = 3000
GOOGLE_DECODE_INTERVAL_SEC = 1  # googlenewsdecoder 요청 사이 쉬는 시간 (429 막기)

# ---- AI 결과 검사 (07 API명세서 4장) ----
HOOK_MAX_CHARS = 40          # 어그로 한 줄 공백 포함 40자 (FR-03-2)
HOOK_ELLIPSIS = "…"
BODY_MIN_CHARS = 600         # 종합 기사 본문 (FR-02-3)
BODY_MAX_CHARS = 1000
BODY_HARD_MIN_CHARS = 300    # 이보다 짧으면 실패로 봄 (07에서 새로 정함)
COPY_MAX_RUN = 50            # 원문과 50자 이상 같은 글자가 이어지면 실패 (FR-02-3 완료 기준)
WORDS_MAX = 5                # 어려운 단어 최대 5개 (FR-02-4)

# ---- 분야 코드(06 4-8) + 검색 키워드(02 기획서 3-1 분야 목록) ----
# 키워드 원본은 기획서 3-1. 여기 값은 그 표를 옮긴 것이다.
CATEGORIES: dict[str, dict] = {
    "politics": {"name": "정치", "deep": {
        "politics_gov": ("대통령·정부", ["대통령실", "국무회의"]),
        "politics_assembly": ("국회·정당", ["국회", "여당", "야당"]),
        "politics_election": ("선거", ["선거", "여론조사"]),
        "politics_northkorea": ("북한", ["북한", "남북"]),
        "politics_diplomacy": ("외교·국방", ["외교부", "국방"]),
    }},
    "economy": {"name": "경제", "deep": {
        "economy_finance": ("금융·증권", ["주식", "금리", "코스피"]),
        "economy_realestate": ("부동산", ["부동산", "아파트", "전세"]),
        "economy_industry": ("산업·기업", ["대기업", "실적"]),
        "economy_jobs": ("취업·창업", ["취업", "채용", "스타트업"]),
        "economy_living": ("생활경제", ["물가", "세금", "환율"]),
    }},
    "society": {"name": "사회", "deep": {
        "society_incident": ("사건·사고", ["사건", "사고"]),
        "society_education": ("교육", ["교육부", "대학", "입시"]),
        "society_labor": ("노동", ["노동", "임금", "파업"]),
        "society_law": ("법·재판", ["재판", "판결", "검찰"]),
        "society_welfare": ("복지·인권", ["복지", "인권", "저출생"]),
    }},
    "world": {"name": "세계", "deep": {
        "world_us": ("미국", ["미국", "백악관"]),
        "world_chinajapan": ("중국·일본", ["중국", "일본"]),
        "world_europe": ("유럽", ["유럽", "EU"]),
        "world_conflict": ("분쟁·중동", ["전쟁", "중동", "우크라이나"]),
        "world_intl": ("국제기구·외교", ["유엔", "정상회담"]),
    }},
    "it": {"name": "IT·컴퓨터", "deep": {
        "it_ai": ("인공지능", ["인공지능", "AI", "생성형 AI"]),
        "it_security": ("보안·해킹", ["해킹", "보안", "개인정보 유출"]),
        "it_mobile": ("모바일·기기", ["스마트폰", "갤럭시", "아이폰"]),
        "it_internet": ("인터넷·플랫폼", ["SNS", "유튜브", "플랫폼"]),
        "it_chip": ("반도체", ["반도체", "HBM"]),
        "it_game": ("게임", ["게임", "e스포츠"]),
    }},
    "science": {"name": "과학", "deep": {
        "science_space": ("우주", ["우주", "NASA", "누리호"]),
        "science_bio": ("생명과학", ["유전자", "바이오", "신약"]),
        "science_physchem": ("물리·화학", ["물리학", "화학", "노벨상"]),
        "science_robot": ("로봇·공학", ["로봇", "자율주행"]),
        "science_energy": ("에너지", ["원전", "배터리", "수소"]),
    }},
    "nature": {"name": "자연·환경", "deep": {
        "nature_climate": ("기후변화", ["기후변화", "탄소중립"]),
        "nature_weather": ("날씨·재난", ["폭염", "태풍", "지진"]),
        "nature_ecology": ("동물·생태", ["멸종위기", "생태계"]),
        "nature_pollution": ("환경오염", ["미세먼지", "플라스틱"]),
    }},
    "culture": {"name": "문화·연예", "deep": {
        "culture_screen": ("영화·드라마", ["영화", "드라마", "OTT"]),
        "culture_music": ("음악", ["K팝", "음원", "콘서트"]),
        "culture_books": ("책·전시", ["베스트셀러", "전시회"]),
        "culture_travel": ("여행", ["여행", "관광"]),
    }},
    "sports": {"name": "스포츠", "deep": {
        "sports_soccer": ("축구", ["축구", "손흥민", "K리그"]),
        "sports_baseball": ("야구", ["프로야구", "KBO", "MLB"]),
        "sports_ballgames": ("농구·배구", ["농구", "배구"]),
        "sports_intl": ("국제대회", ["올림픽", "월드컵"]),
    }},
    "life": {"name": "생활·건강", "deep": {
        "life_health": ("건강·의학", ["건강", "질병", "병원"]),
        "life_food": ("음식", ["맛집", "식품"]),
        "life_fashion": ("패션·뷰티", ["패션", "뷰티"]),
        "life_family": ("육아·반려동물", ["육아", "반려동물"]),
    }},
}

# 시험 실행용 기본 분야 (Firestore settings/me 대신). 환경변수로 바꿀 수 있다.
TRIAL_FIRST = os.environ.get("TRIAL_FIRST_CATEGORY", "science")
TRIAL_DEEP = os.environ.get("TRIAL_DEEP_CATEGORY", "science_space")
TRIAL_SECOND = os.environ.get("TRIAL_SECOND_CATEGORY", "economy")


def deep_keywords(deep_code: str) -> list[str]:
    """깊은 분야 코드 -> 검색 키워드 목록."""
    for cat in CATEGORIES.values():
        if deep_code in cat["deep"]:
            return list(cat["deep"][deep_code][1])
    raise KeyError(deep_code)


def first_keyword_of_category(cat_code: str) -> str:
    """큰 분야의 대표 키워드 = 첫 깊은 분야의 첫 키워드 (FR-01-9)."""
    first_deep = next(iter(CATEGORIES[cat_code]["deep"].values()))
    return first_deep[1][0]
