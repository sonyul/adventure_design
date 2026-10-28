# 뉴스 봐 — API 명세서

| 항목 | 내용 |
|---|---|
| 문서 유형 | 07 API 명세서 |
| 버전 | v1.0 |
| 작성일 | 2026-10-28 |
| 작성방식 | 신규 (시험 실행 스크립트 `script/`와 함께 작성 — 지시문·검사 규칙은 코드와 같은 내용) |
| 문서 상태 | ⚠ 부분 — 창구 형식·AI 지시문·검사 규칙은 작성 완료. **실제 Gemini 호출 결과는 아직 없음**(키 미발급), 어그로 예시 제목 15개는 **초안 — 사용자가 교체 예정** |
| 근거 문서 | [기획서](02_기획서.md) (v1.4) · [기능명세서](03_기능명세서.md) (v1.6) · [데이터 모델](06_데이터모델_ERD.md) (v1.1) · [아키텍처·ADR](08_아키텍처_ADR.md) (v1.1) |
| 함께 보는 코드 | [`script/`](../../script/README.md) — 시험 실행 스크립트, [`script/prompts/`](../../script/prompts/) — 지시문 글 파일 |
| 추적표 | [INDEX·추적표](01_INDEX_RTM.md) (🔴 미작성) — [8장](#8-기능fr--창구--ai-작업-추적표) 표를 "API" 열에 **등재 예정** |

> **이 문서를 읽는 법**
> - 이 서비스에는 **우리가 직접 만든 서버 창구가 없습니다**(03 8장 ✅, 08 ADR-001 ✅). 그래서 이 문서는 ① 파이썬 스크립트·앱이 부르는 **바깥 창구 6개(A1~A6)** 의 요청·응답 모양과 ② 스크립트가 AI에게 시키는 **작업 5개(T1~T5)** 의 지시문·결과 형식·검사 규칙을 정합니다.
> - **✅ 확정** = 앞 문서에서 이미 정해진 것 · **✅ 추천대로** = 이 문서에서 처음 정한, 나중에 쉽게 고칠 수 있는 기술 세부(사용자 기준 "고치기 쉬운 것은 추천대로") · **🔍 확인(날짜)** = 이번에 공식 문서·실제 실행으로 확인한 사실 · **❓ 확인 못 함** = 찾아봤지만 공식 근거를 못 찾은 것
> - 상태 기호: ✅ 완료 · ⚠ 부분 · 🔴 미작성 · ⏳ 진행
>
> **약어·용어 풀이**
> - **API**(Application Programming Interface): 프로그램끼리 정해진 방식으로 데이터를 주고받는 창구. 이 문서에서는 "창구"라고도 씁니다.
> - **엔드포인트**(endpoint): 창구의 정확한 인터넷 주소
> - **HTTP**(HyperText Transfer Protocol): 웹에서 요청·응답을 주고받는 규칙. `GET`(가져오기)·`POST`(보내기) 같은 방식과 `200`(성공)·`429`(너무 많이 요청함) 같은 **상태 코드**가 있습니다.
> - **RSS**(Really Simple Syndication): 웹사이트가 새 글 목록을 정해진 형식(XML)으로 내보내는 방식
> - **XML**(eXtensible Markup Language) · **JSON**(JavaScript Object Notation): 데이터를 글자로 적는 형식. JSON은 `{"이름": 값}` 모양입니다.
> - **스키마**(schema): 데이터의 "모양 약속" — 어떤 이름의 칸이 어떤 종류의 값으로 오는지
> - **지시문**(prompt, 프롬프트): AI에게 "무엇을, 어떤 규칙으로, 어떤 모양으로 답하라"고 주는 글
> - **RPM**(Requests Per Minute, 분당 요청 수) · **RPD**(Requests Per Day, 하루 요청 수) · **TPM**(Tokens Per Minute, 분당 토큰 수 — 토큰은 AI가 글을 세는 단위)
> - **SDK**(Software Development Kit): 어떤 서비스를 쉽게 부르도록 회사가 만들어 준 부품 묶음 (예: `google-genai`)
> - **KST**(한국 표준시) · **UTC**(세계 표준시) · **FR**(기능 요구) · **NFR**(비기능 요구) · **ADR**(설계 결정 기록) — 앞 문서와 같음

---

## 1. 창구(엔드포인트) 목록

### 1-1. 바깥 창구 6개 (번호는 [03 8장](03_기능명세서.md#8-api-요약) ✅ 그대로)

| # | 창구 | 엔드포인트 / 호출 방법 | 방식 | 누가 부르나 (파일) | 인증 | 관련 FR | 상태 |
|:---:|---|---|:---:|---|---|---|:---:|
| A1 | 구글 뉴스 "주요 뉴스" RSS (한국어) | `https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko` | GET | 스크립트 `collect.py` | 없음 | FR-01-4 | ✅ 🔍 실제 호출 성공 (2026-10-28) |
| A1' | 구글 뉴스 링크 → 원문 주소 | `googlenewsdecoder.gnewsdecoder(링크)` 부품 함수 (속으로 구글 창구를 부름) | — | 스크립트 `google_link.py` | 없음 | FR-01-4, FR-02-2·5 (C4, ADR-007) | ✅ 🔍 2회 모두 15/15 성공 (2026-10-28) |
| A2 | 네이버 뉴스 검색 API | `https://openapi.naver.com/v1/search/news.json` | GET | 스크립트 `collect.py` | 네이버 Client ID·Secret (요청 머리글) | FR-01-5·6·9 | ✅ 🔍 공식 문서 확인 / ⏳ 키 없어 실제 호출 전 |
| A3 | 언론사 원문 웹페이지 | 원문 기사 주소 (A1'·A2에서 얻음) | GET | 스크립트 `extract.py` (`trafilatura`) | 없음 | FR-02-2 | ✅ 🔍 11/15·12/15 추출 성공 (2026-10-28, 2회) |
| A4 | Gemini API (Flash-Lite, 무료 요금제) | `google-genai` SDK의 `client.models.generate_content(...)` (속 주소 `https://generativelanguage.googleapis.com/v1beta/models/{모델}:generateContent`) | POST | 스크립트 `ai_client.py` (유일한 창구, ADR-008) | Gemini API 키 | FR-02-1·3·4, FR-03-2, FR-04-2, FR-01-9 | ✅ 형식 확정 / ⏳ 키 없어 실제 호출 전 |
| A5 | Firestore (스크립트 쪽) | `firebase-admin` SDK (`db.collection(...)`) | — | 스크립트 `settings_store.py` (운영판) | 서비스 계정 열쇠 (GitHub Secrets) | FR-01-2, FR-02-6 | ✅ 모양만 (시험판은 Firestore 안 씀) |
| A6 | Firestore (앱 쪽) | 안드로이드 Firestore SDK | — | 앱 | 익명 로그인 + 보안 규칙 ([09](09_보안_개인정보.md)) | FR-01-1·2·7·8, FR-02-7, FR-04-2 | ✅ 모양만 |

### 1-2. AI 작업 5개 (A4를 부르는 방식)

> AI 호출은 모두 `ai_client.py`의 함수 하나(`generate_json(지시문, 입력)`)를 거칩니다 (ADR-008 ✅). 작업 이름 T1~T5는 이 문서에서 붙인 번호입니다 (✅ 추천대로).

| # | 작업 | 지시문 파일 | 회차당 호출 | 관련 FR | 실패하면 (✅ 03) |
|:---:|---|---|:---:|---|---|
| T1 | 오늘의 화제 고르기 (후보 5개 중 1~3개) | [`prompts/01_pick_today.txt`](../../script/prompts/01_pick_today.txt) | 1 | FR-01-4, 03 v1.4 상자 | 위에서 3개 (`PICK_FALLBACK`) |
| T2 | 네이버 기사 묶기 + 고르기 (페이지마다) | [`prompts/02_group_pick.txt`](../../script/prompts/02_group_pick.txt) | 2 (관심·추천) | FR-02-1, FR-01-5·6 | 묶기 실패: 최신순 1개씩 (`GROUP_FALLBACK`) / 고르기만 실패: 위에서 3개 (`PICK_FALLBACK`) |
| T3 | 종합 기사 + 어려운 단어 해설 + 어그로 한 줄 (묶음마다 1번) | [`prompts/03_write_article.txt`](../../script/prompts/03_write_article.txt) | 최대 9 | FR-02-3·4, FR-03-1·2 | 1번 다시 시도 → 그 묶음 건너뜀 (`AI_GROUP_SKIPPED`) |
| T4 | 다른 분야 한 줄 (8개 분야 한 번에) | [`prompts/04_other_lines.txt`](../../script/prompts/04_other_lines.txt) | 1 | FR-01-9 | 칸 전체 숨김 (`OTHER_LINES_HIDDEN`) |
| T5 | 알림용 한 줄 고르기 | [`prompts/05_pick_notify.txt`](../../script/prompts/05_pick_notify.txt) | 1 | FR-04-2 | 원문 기사 수가 가장 많은 기사 (`NOTIFY_FALLBACK`) |
| — | 어그로 예시 제목 15개 (T3·T4에 끼워 넣음) | [`prompts/hook_examples.txt`](../../script/prompts/hook_examples.txt) | — | FR-03-1 | 파일 없음/비어 있음 → 규칙만으로 (`EXAMPLES_FILE_MISSING`) |

- 회차당 보통 호출 수: T1 1 + T2 2 + T3 최대 9 + T4 1 + T5 1 = **최대 14번**, 하루 3회차 = **최대 42번** (NFR-05 ✅ 50번 이하와 같은 계산).

### 1-3. 🔍 최신 사실 확인 (확인일 2026-10-28)

> 발표 기준 "최신 정보·출처 확인"을 위해 숫자마다 출처를 붙였습니다. **공식 문서에 없는 숫자는 "공식 아님"으로 따로 표시**합니다.

**① Gemini 무료 요금제에서 쓸 수 있는 Flash-Lite 모델** — 공식: [모델 목록](https://ai.google.dev/gemini-api/docs/models) (페이지 갱신 2026-10-22), [요금](https://ai.google.dev/gemini-api/docs/pricing) (갱신 2026-10-27)

| 모델 이름 (코드에 쓰는 값) | 상태 (공식) | 무료 요금제 | 무료 요금제 데이터 활용 | 이 프로젝트 |
|---|---|---|---|---|
| `gemini-3.5-flash-lite` | 안정판(Stable) | ✅ 입력·출력 무료 | 구글 제품 개선에 쓰임 = **예** | 교체 후보 |
| **`gemini-3.1-flash-lite`** | 안정판(Stable) | ✅ 입력·출력 무료 | 예 | **기본값으로 채택** (✅ 추천대로, 아래 ③ 이유) |
| `gemini-2.5-flash-lite` | 지원은 계속하나 **예전에 쓰던 사용자만** 접근 | ✅ | 예 | 쓰지 않음 |
| `gemini-3.1-flash-lite-preview`, `gemini-2.0-flash-lite` | **서비스 종료(Shut down)** | — | — | 쓰지 않음 |

**② 무료 한도 숫자 (RPM·RPD)**

| 출처 | 내용 | 공식? |
|---|---|:---:|
| [공식 rate limit 페이지](https://ai.google.dev/gemini-api/docs/rate-limits) (갱신 2026-10-26) | 무료 요금제의 RPM·RPD **숫자를 적어 두지 않음**. "활성 한도는 AI Studio에서 보라"고 안내 → 내 프로젝트 기준 한도는 [AI Studio 한도 화면](https://aistudio.google.com/rate-limit)(로그인 필요)에서 확인 | ✅ 공식 |
| [tilnote 정리글](https://tilnote.io/pages/6a51b3398d9a59d14c1c174c) (2026-07-11, AI Studio 한도 화면을 옮겨 적은 글) | Gemini 3.1 Flash Lite **15 RPM · 250K TPM · 500 RPD** / Gemini 2.5 Flash Lite 10 RPM · 20 RPD / Gemini 3.5 Flash 5 RPM · 20 RPD. **3.5 Flash-Lite 숫자는 없음** | ❌ 공식 아님 (3개월 전) |

- 기획서 5-4의 "외부 자료 기준 하루 약 500회(Flash는 약 20회)"는 위 정리글의 **Gemini 3.1 Flash-Lite 500 RPD / 3.5 Flash 20 RPD** 와 같은 숫자로 보입니다. 다만 **공식 숫자가 아니므로**, 발표·문서에는 "공식 문서는 한도를 AI Studio 화면에서만 보여줌 → 키 발급 후 화면에서 확인한 값"을 적어야 합니다. ❓ 확인 못 함: 3.5 Flash-Lite의 무료 RPM·RPD, 그리고 지금(2026-10-28) 3.1 Flash-Lite 숫자가 그대로인지.
- 우리 사용량(하루 최대 42번 + 재시도)은 500 RPD가 맞다면 **약 8~10%** 수준입니다. 분당 한도(15 RPM이 맞다면)는 회차당 14번을 **4.5초 간격**으로 부르면 넘지 않습니다(`config.AI_MIN_INTERVAL_SEC`, ✅ 추천대로).

**③ 기본 모델을 `gemini-3.1-flash-lite`로 정한 이유 (✅ 추천대로 — 설정값 한 줄이라 쉽게 바꿈)**

| 기준 | `gemini-3.1-flash-lite` | `gemini-3.5-flash-lite` | `gemini-3.8-flash` (Flash) |
|---|---|---|---|
| 공식 상태 | 안정판, 무료 | 안정판(가장 새것), 무료 | 안정판, 무료 |
| 무료 한도 근거 | 공식 아님이지만 **숫자가 있는 유일한 Flash-Lite** (500 RPD) | 숫자 근거 없음 | Flash 계열은 20 RPD 수준이라는 정리 → 하루 42번에 **부족** |
| 기획서 결정(Flash-Lite)과 | 맞음 | 맞음 | 어긋남 |

- 키를 받은 뒤 AI Studio 한도 화면에서 3.5 Flash-Lite의 RPD가 **50 이상**이면 바꿔도 됩니다: `$env:GEMINI_MODEL = "gemini-3.5-flash-lite"` (NFR-09 ✅ 교체 용이성).

**④ 그 밖의 창구·부품**

| 대상 | 확인한 사실 | 출처 (확인일 2026-10-28) |
|---|---|---|
| 네이버 뉴스 검색 API | 하루 호출 한도 **25,000회** (검색 API 전체 합산, Client ID별). 응답 항목: `title`·`originallink`·`link`·`description`·`pubDate` — **언론사 이름 항목은 없음** | [공식 문서](https://developers.naver.com/docs/serviceapi/search/news/news.md) |
| `google-genai` (구글 공식 Gemini SDK) | 최신 **2.33.0** (2026-10-23 배포), 파이썬 3.10 이상 | [PyPI](https://pypi.org/project/google-genai/) |
| `googlenewsdecoder` | 최신 **0.2.2** (2026-10-18 배포), **파이썬 3.11 이상**. 응답 키는 `success`·`decoded_url` (실측) | [PyPI](https://pypi.org/project/googlenewsdecoder/) |
| `trafilatura` | 최신 **2.3.1** (2026-10-06 배포), 파이썬 3.10 이상 | [PyPI](https://pypi.org/project/trafilatura/) |
| `feedparser` / `requests` / `firebase-admin` | 6.0.14 / 2.34.2 / 7.7.0 | [PyPI](https://pypi.org/) (각 패키지 JSON 정보) |

- 버전은 [`script/requirements.txt`](../../script/requirements.txt)에 고정했습니다 (ADR-011 ✅ "버전 고정"). `firebase-admin`은 시험판에서 쓰지 않아 목록에서 뺐습니다(주석으로만 남김).

---

## 2. 요청·응답 스키마 — 바깥 창구 (A1~A6)

> 아래 예시 값은 **모양을 보여주려고 지어낸 값**입니다(06 3-8과 같은 방식). 실제 실행 결과는 [7장](#7-시험-실행-결과-2026-10-28)에 있습니다.

### 2-1. A1 구글 뉴스 "주요 뉴스" RSS (FR-01-4)

**요청**

```
GET https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko
```

| 파라미터 | 값 | 뜻 |
|---|---|---|
| `hl` | `ko` | 화면 언어 = 한국어 |
| `gl` | `KR` | 나라 = 한국 |
| `ceid` | `KR:ko` | 한국판 한국어 뉴스 |

**응답 (XML, 필요한 부분만)** — 🔍 2026-10-28 실제 응답에서 확인: 항목 34개, 각 항목의 `description` 안에 같은 사건 기사 목록(최대 5개)이 들어 있음

```xml
<item>
  <title>지하철 노조 내일 파업 예고 - 한빛일보</title>          <!-- 대표 제목 + " - 언론사" -->
  <link>https://news.google.com/rss/articles/CBMi...?oc=5</link> <!-- 구글 경유 링크 (C4) -->
  <pubDate>Wed, 28 Oct 2026 03:49:00 GMT</pubDate>            <!-- 대표 기사 시각 (UTC) -->
  <source url="https://www.hanbit.co.kr">한빛일보</source>
  <description>
    <ol>
      <li><a href="https://news.google.com/rss/articles/AAA...">지하철 노조 내일 파업 예고</a>&nbsp;&nbsp;<font color="#6f6f6f">한빛일보</font></li>
      <li><a href="https://news.google.com/rss/articles/BBB...">출근길 비상…노사 막판 협상</a>&nbsp;&nbsp;<font color="#6f6f6f">누리신문</font></li>
      <!-- … 최대 5개 -->
    </ol>
  </description>
</item>
```

**스크립트가 읽는 방법 → 데이터 모델 대응 (✅ 추천대로)**

| RSS 위치 | 스크립트 값 | 06 필드 (D5 출처) |
|---|---|---|
| `item` 1개 | 묶음 1개 (위에서 5개 = 후보) | `articles[]` 1칸의 재료 |
| `description` 의 `<li><a>` 글자 | 원문 제목 | `sources[].title` |
| `description` 의 `<li><a href>` | 구글 경유 링크 → A1'로 원문 주소 | `sources[].url`, `linkType` |
| `description` 의 `<font>` 글자 | 언론사 | `sources[].press` |
| `item/pubDate` | 대표 기사(첫 번째) 시각만. 나머지는 없음 | `sources[].publishedAt` (첫 번째만 값, 나머지 `null`) |
| (`description`에 목록이 없을 때) | `item/title`에서 " - 언론사"를 떼어 대표 기사 1개만 | — |

- 요약(본문 몇 줄)은 **주지 않습니다** (08 A1 ✅). 그래서 본문 추출이 모두 실패하면 제목만으로 작성합니다(FR-02-2 ✅).

### 2-2. A1' 구글 뉴스 링크 → 원문 주소 (ADR-007 ✅)

```python
from googlenewsdecoder import gnewsdecoder
res = gnewsdecoder("https://news.google.com/rss/articles/CBMi...", interval=1, timeout=10)
```

| 응답 (🔍 0.2.2 실측) | 뜻 | 스크립트 처리 |
|---|---|---|
| `{"success": true, "decoded_url": "https://www.hanbit.co.kr/article/123"}` | 성공 | `url` = 원문 주소, `linkType` = `original` |
| `{"success": false, "message": "..."}` 또는 예외 | 실패 (구글이 막음·방식 변경 등) | 구글 링크 그대로, `linkType` = `google`, 본문 추출 `not_tried` |

- `interval=1`: 요청 사이 1초 쉼 (구글이 "너무 많은 요청(429)"으로 막지 않게, ✅ 추천대로).
- ⚠ 부품 문서·예전 글에는 응답 키가 `status`로 적힌 경우가 있으나 0.2.2 실제 응답은 `success`입니다. 스크립트는 둘 다 받습니다.

### 2-3. A2 네이버 뉴스 검색 API (FR-01-5·6·9) — 🔍 [공식 문서](https://developers.naver.com/docs/serviceapi/search/news/news.md) 확인 2026-10-28

**요청**

```
GET https://openapi.naver.com/v1/search/news.json?query=%EC%9A%B0%EC%A3%BC&display=20&start=1&sort=date
X-Naver-Client-Id: {Client ID}
X-Naver-Client-Secret: {Client Secret}
```

| 파라미터 | 필수 | 공식 범위 | 우리 값 | 근거 |
|---|:---:|---|---|---|
| `query` | ○ | UTF-8 글자 | 깊은 분야 키워드 1개 (예 `우주`) | 02 3-1 분야 목록 ✅ |
| `display` | | 1~100 (기본 10) | **20** (다른 분야 한 줄은 **10**) | FR-01-5 ✅, FR-01-9 ✅ |
| `start` | | 1~1000 (기본 1) | 1 | — |
| `sort` | | `sim`(정확도) / `date`(날짜순) | **`date`** | FR-01-5 ✅ 최신순 |

**응답 (JSON)**

```json
{
  "lastBuildDate": "Wed, 28 Oct 2026 11:01:35 +0900",
  "total": 25660,
  "start": 1,
  "display": 20,
  "items": [
    {
      "title": "누리호 5차 발사 <b>우주</b>로 출발",
      "originallink": "https://www.hanbit.co.kr/news/2026/10/28/123",
      "link": "https://n.news.naver.com/mnews/article/000/0000000123",
      "description": "한국항공<b>우주</b>연구원은 28일 … 밝혔다.",
      "pubDate": "Wed, 28 Oct 2026 10:05:00 +0900"
    }
  ]
}
```

| 응답 항목 | 뜻 (공식) | 스크립트 처리 → 06 필드 |
|---|---|---|
| `title` | 제목. 검색어 부분이 `<b>`로 감싸짐 | 태그·`&quot;` 같은 글자 표시 제거 → `sources[].title` |
| `originallink` | 원문 주소 | 있으면 `url`, `linkType`=`original` |
| `link` | 네이버 뉴스 주소 (네이버에 없는 기사면 원문 주소) | `originallink`가 비면 `url`, `linkType`=`naver` (06 4-5 ✅) |
| `description` | 요약 몇 줄 (`<b>` 포함) | 태그 제거 → 본문 추출 실패 시 AI 입력으로 사용 (FR-02-2 ✅), 저장 안 함 |
| `pubDate` | 네이버에 제공된 시각 | 24시간(부족하면 48시간) 거르기 (FR-01-5 ✅) → `publishedAt` |

**언론사 이름 결정 (06 3-6 ⚠ 해결, ✅ 추천대로)** — 공식 응답에 **언론사 항목이 없음**을 확인했습니다. 그래서 `press`에는 **원문 주소의 사이트 이름(도메인)** 을 넣습니다(예: `www.hanbit.co.kr` → `hanbit.co.kr`, 앞의 `www.`·`m.` 제거). 화면에 도메인 대신 한국어 언론사 이름을 보이고 싶으면 나중에 `config.py`에 "도메인 → 언론사 이름" 짧은 대응표를 더하면 됩니다(저장 칸은 같음).

### 2-4. A3 언론사 원문 웹페이지 (FR-02-2)

| 구분 | 내용 |
|---|---|
| 요청 | `GET {원문 주소}` — 머리글 `User-Agent`(일반 브라우저 이름), `Accept-Language: ko-KR`. **10초** 넘으면 포기 (FR-02-2 ✅) |
| 처리 | 받은 웹페이지(바이트 그대로)를 `trafilatura.extract(..., favor_precision=True)`에 넣어 본문 글자만 뽑음 |
| 결과 코드 (06 4-7 ✅) | `ok`(200자 이상 → 앞 3,000자만 사용) · `open_failed`(오류·10초 초과) · `too_short`(200자 미만) · `empty`(빈 값) · `not_tried`(원문 주소 없음) |
| 저장 | **본문은 메모리에서만 쓰고 저장하지 않음** (NFR-08 ✅). 시험판 결과 파일에도 글자 **수**만 남김 |

### 2-5. A4 Gemini API (요청·응답 바깥 모양) — 세부는 [3장](#3-ai-작업별-지시문과-json-결과-형식-t1t5)

```python
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])   # 키는 환경변수에서만 (NFR-06)
resp = client.models.generate_content(
    model="gemini-3.1-flash-lite",                    # config.AI_MODEL (환경변수 GEMINI_MODEL로 바꿈)
    contents=json.dumps(입력, ensure_ascii=False),    # 작업 입력 (JSON 글자)
    config=types.GenerateContentConfig(
        system_instruction=지시문,                      # prompts/0N_*.txt 내용
        response_mime_type="application/json",         # JSON으로만 답하게 함
        temperature=0.7,
    ),
)
text = resp.text   # → json.loads → 작업별 검사(4장)
```

| 항목 | 값 (✅ 추천대로) | 이유 |
|---|---|---|
| 지시문 위치 | `system_instruction` (지시문 파일 내용) | 지시문과 입력 데이터를 섞지 않음 |
| 입력 | 작업별 JSON (3장 "입력 예") | 번호(`no`)로 기사를 가리키게 해 AI가 링크를 지어내지 못하게 함 |
| 출력 형식 | `response_mime_type="application/json"` | JSON이 아닌 답을 줄임. 그래도 스크립트가 다시 검사 |
| 출력 스키마 강제(`response_json_schema`) | **쓰지 않음** | 가장 쉬운 방법 우선. 모양은 지시문에 적고 4장 검사로 걸러 냄. 실패가 잦으면 그때 추가 |
| 호출 간격 | 최소 4.5초 | 15 RPM(공식 아님) 가정 |

### 2-6. A5·A6 Firestore (모양만 — 저장 구조 원본은 [06](06_데이터모델_ERD.md))

| 누가 | 요청 모양 | 06 근거 |
|---|---|---|
| 스크립트 (A5) | `db.collection("settings").document("me").get()` → 분야 읽기 | 3-1 |
| 스크립트 (A5) | `db.collection("runs").document(runId).set({... status: "running"})` → 끝날 때 다시 `set` | 3-2 |
| 스크립트 (A5) | `db.collection("editions").order_by("createdAt", direction="DESCENDING").limit(1).get()` → 직전 회차(복사용) | 3-3 |
| 스크립트 (A5) | `db.collection("editions").document(editionId).set({...})` → 한 번 쓰고 끝 | 3-3 |
| 앱 (A6) | `collection("editions").orderBy("createdAt", Query.Direction.DESCENDING).limit(1).get()` → 최신 회차 1개 | 5-1 |
| 앱 (A6) | `collection("settings").document("me").set({firstCategory, deepCategory, secondCategory, updatedAt: serverTimestamp(), schemaVersion: 1})` | 3-1, 5-1 |

- 시험판(`script/`)은 Firestore 대신 같은 모양의 JSON 파일(`sample_output/run_*.json`의 `run`·`edition`)로 저장합니다.

---

## 3. AI 작업별 지시문과 JSON 결과 형식 (T1~T5)

> **원칙 (✅ ADR-008 + 추천대로)**
> 1. 지시문은 코드가 아니라 [`script/prompts/`](../../script/prompts/) 글 파일에 둡니다. **아래 "지시문 전문"은 그 파일과 글자 하나까지 같습니다** — 단위 시험 `TestDocMatchesPromptFiles`가 이 문서와 파일을 비교해 확인합니다.
> 2. AI가 돌려줄 JSON 칸 이름은 **[06 데이터 모델](06_데이터모델_ERD.md)의 필드 이름과 같게** 정했습니다(`title`·`body`·`conclusion`·`words[].word`·`words[].explanation`·`hookLine`). 그래서 검사만 통과하면 그대로 옮겨 담습니다.
> 3. AI에게는 링크·언론사를 쓰게 하지 않습니다. 기사는 **번호(`no`)** 로만 가리키고, 링크·언론사·날짜는 스크립트가 원래 데이터에서 붙입니다(출처를 지어낼 수 없게).
> 4. `{{HOOK_EXAMPLES}}` 자리에는 [`hook_examples.txt`](../../script/prompts/hook_examples.txt)의 제목들이 `- 제목` 모양으로 한 줄씩 들어갑니다. 파일이 없거나 비면 `(예시 없음 - 위 규칙만 따른다)`가 들어가고 경고 `EXAMPLES_FILE_MISSING`을 남깁니다(FR-03-1 ✅).

### 3-1. T1 오늘의 화제 고르기 (FR-01-4, 03 v1.4 상자 ✅)

**지시문 전문** — 파일 [`script/prompts/01_pick_today.txt`](../../script/prompts/01_pick_today.txt)

<!-- prompt-file: 01_pick_today.txt -->
```text
너는 한국어 뉴스 앱 "뉴스 봐"의 편집자다.
아래 입력은 지금 구글 뉴스 "주요 뉴스"에 올라온 기사 묶음 후보 목록이다. 각 후보에는 번호(no), 대표 제목(title), 같은 사건을 다룬 다른 기사 제목들(related)이 있다.

할 일:
- 상식으로 알아 두면 좋거나(모르면 대화에서 뒤처질 만한 시사), 흥미로운 후보만 고른다.
- 최소 1개, 최대 3개를 고른다. 볼 만한 것이 적으면 적게 고른다.
- 같은 사건을 다룬 후보를 2개 이상 고르지 않는다.
- 중요한 것부터 순서대로 적는다.

출력 규칙:
- 반드시 아래 모양의 JSON 하나만 출력한다. 설명 글이나 코드 블록 표시를 붙이지 않는다.
{"picked": [후보 번호, ...], "reason": "고른 이유 한 문장"}
- picked에는 입력에 있는 번호(no)만 넣는다.
```

**입력 예** (A1 위에서 5개 묶음)

```json
{"candidates": [
  {"no": 1, "title": "지하철 노조 내일 파업 예고", "related": ["출근길 비상…노사 막판 협상", "파업 땐 열차 운행 절반"]},
  {"no": 2, "title": "한국 우주선 달 궤도 진입 성공", "related": ["달 궤도선 성공 의미는"]},
  {"no": 3, "title": "프로야구 시상식 일정 발표", "related": []},
  {"no": 4, "title": "다음 달 전기요금 인상", "related": ["가구당 월 1천원 더"]},
  {"no": 5, "title": "파업 앞둔 지하철, 시민 불편 우려", "related": []}
]}
```

**출력 스키마**

| 칸 | 자료형 | 필수 | 뜻 |
|---|---|:---:|---|
| `picked` | 정수 목록 | ○ | 고른 후보 번호 1~3개, 중요한 순서 |
| `reason` | 글자 | △ | 고른 이유 (저장 안 함, 실행 로그용) |

```json
{"picked": [1, 2, 4], "reason": "출근·생활에 바로 영향이 있고 대화거리가 되는 소식"}
```

### 3-2. T2 네이버 기사 묶기 + 고르기 (FR-02-1, FR-01-5·6 ✅)

**지시문 전문** — 파일 [`script/prompts/02_group_pick.txt`](../../script/prompts/02_group_pick.txt)

<!-- prompt-file: 02_group_pick.txt -->
```text
너는 한국어 뉴스 앱 "뉴스 봐"의 편집자다.
아래 입력은 한 분야(field)에서 최근에 나온 네이버 뉴스 검색 결과 목록이다. 각 기사에는 번호(no), 제목(title), 요약(summary)이 있다.

할 일 1 - 묶기:
- 같은 사건(같은 일)을 다룬 기사끼리 한 묶음으로 묶는다.
- 한 묶음에는 기사를 최대 5개까지만 넣는다. 더 있으면 내용이 풍부해 보이는 5개만 넣는다.
- 다른 기사와 묶이지 않는 기사는 1개짜리 묶음이 될 수 있다.
- 한 기사는 한 묶음에만 넣는다.
- 묶음은 많이 보도된 순서(기사 수가 많은 순서)로 정렬한다.

할 일 2 - 고르기:
- 만든 묶음 중 상식으로 알 만하거나 흥미로운 것만 고른다. 최소 1개, 최대 3개. 볼 만한 것이 적으면 적게 고른다.
- 광고·홍보성 기사, 단순 인사·부고, 주가 시세를 나열한 기사는 고르지 않는다.

출력 규칙:
- 반드시 아래 모양의 JSON 하나만 출력한다. 설명 글이나 코드 블록 표시를 붙이지 않는다.
{"groups": [{"topic": "묶음 주제 한 줄", "items": [기사 번호, ...]}, ...], "picked": [묶음 순번, ...]}
- groups의 순번은 1부터 센다(첫 번째 묶음 = 1).
- items에는 입력에 있는 기사 번호(no)만 넣는다.
- picked에는 고른 묶음의 순번을 1~3개 넣는다.
```

**입력 예** (관심 분야 페이지: 키워드 3개 × 최신순 20개 → 24시간 거르기·중복 제거)

```json
{"field": "과학",
 "articles": [
  {"no": 1, "title": "누리호 5차 발사 성공", "summary": "한국항공우주연구원은 28일 …"},
  {"no": 2, "title": "누리호, 위성 6기 궤도에 올려", "summary": "…"},
  {"no": 3, "title": "NASA 새 우주망원경 첫 사진 공개", "summary": "…"},
  {"no": 4, "title": "[부고] ○○○ 연구원 별세", "summary": "…"}
 ]}
```

**출력 스키마**

| 칸 | 자료형 | 필수 | 뜻 |
|---|---|:---:|---|
| `groups` | 목록 | ○ | 묶음 목록, 많이 보도된 순서 |
| `groups[].topic` | 글자 | △ | 묶음 주제 한 줄 (실행 로그용) |
| `groups[].items` | 정수 목록 | ○ | 그 묶음의 기사 번호 (최대 5개) |
| `picked` | 정수 목록 | ○ | 고른 **묶음 순번**(1부터) 1~3개 |

```json
{"groups": [
   {"topic": "누리호 5차 발사 성공", "items": [1, 2]},
   {"topic": "NASA 우주망원경 첫 사진", "items": [3]},
   {"topic": "부고", "items": [4]}
 ],
 "picked": [1, 2]}
```

### 3-3. T3 종합 기사 + 어려운 단어 해설 + 어그로 한 줄 (FR-02-3·4, FR-03-1·2 ✅ — 묶음당 1회 호출)

**지시문 전문** — 파일 [`script/prompts/03_write_article.txt`](../../script/prompts/03_write_article.txt)

<!-- prompt-file: 03_write_article.txt -->
```text
너는 한국어 뉴스 앱 "뉴스 봐"의 기자다. 독자는 뉴스를 잘 찾아보지 않는 대학생·사회초년생이고, 전문가가 아니다.
아래 입력은 같은 사건을 다룬 원문 기사 1~5개다. 각 기사에는 언론사(press), 제목(title), 본문 또는 요약(text)이 있다. text가 비어 있으면 제목만 참고한다.

할 일 1 - 종합 기사 쓰기:
- 여러 기사의 내용을 모아 한 편의 종합 기사로 새로 쓴다. 무슨 일이 있었는지, 왜 중요한지, 앞으로 어떻게 될지까지 담아 결론이 있는 글로 만든다.
- 제목(title): 1줄. 사실을 담백하게 쓴다.
- 본문(body): 공백 포함 600~1,000자. 쉬운 말과 친근한 존댓말("~해요", "~이에요")로 쓴다. 문단은 줄바꿈으로 나눈다.
- 한 줄 결론(conclusion): 독자가 기억하면 좋을 한 문장.
- 원문 문장을 그대로 옮기지 않는다. 특히 원문과 똑같은 글자가 50자 이상 이어지면 안 된다. 반드시 자기 말로 다시 쓴다.
- 입력 기사에 없는 사실을 지어내지 않는다. 기사끼리 내용이 다르면 "~라는 보도도 있어요"처럼 구분해 쓴다.
- 사람 이름·숫자·날짜는 입력 기사에 있는 그대로 쓴다.

할 일 2 - 어려운 단어 해설:
- 본문(body)에 실제로 쓴 단어 중 비전공자가 어려워할 단어를 3~5개 고른다.
- word에는 본문에 나온 글자를 그대로(조사를 빼고) 적는다.
- explanation은 1~2문장, 100자 안팎의 쉬운 설명으로 쓴다.

할 일 3 - 어그로 한 줄(hookLine):
- 종합 기사를 토대로, 알림에서 보고 눌러 보고 싶어지는 한 문장을 1개 만든다.
- 공백 포함 40자 이내.
- 극단적인 단어(예: "내일", "지금", "죽음", "멸망")와 유행어·친근한 말투를 써도 된다. 단, 너무 자극적이지 않은 선을 지킨다.
- 과장은 허용한다. 그러나 다음은 절대 쓰지 않는다.
  1) 사실과 정반대인 내용 (예: 살아 있는 사람이 죽었다고 쓰기, 취소된 일을 확정됐다고 쓰기)
  2) 실존 인물을 비난하거나 조롱하는 문장
- 아래 예시 제목들의 말투를 참고하되, 그대로 베끼지 않는다.

[어그로 예시 제목]
{{HOOK_EXAMPLES}}

출력 규칙:
- 반드시 아래 모양의 JSON 하나만 출력한다. 설명 글이나 코드 블록 표시를 붙이지 않는다.
{"title": "...", "body": "...", "conclusion": "...", "words": [{"word": "...", "explanation": "..."}], "hookLine": "..."}
```

**입력 예** (묶음 1개, 원문 1~5개. `text` = 추출 본문 3,000자 이하 → 없으면 네이버 요약 → 없으면 빈 값)

```json
{"articles": [
  {"press": "한빛일보", "title": "지하철 노조 내일 파업 예고", "text": "서울 지하철 노동조합이 … (본문 최대 3,000자)"},
  {"press": "누리신문", "title": "출근길 비상…노사 막판 협상", "text": ""}
]}
```

**출력 스키마 → 06 D3·D4 대응**

| AI 칸 | 자료형 | 필수 | 06 필드 | 규칙 (근거) |
|---|---|:---:|---|---|
| `title` | 글자 | ○ | `articles[].title` | 1줄 (FR-02-3 ✅) |
| `body` | 글자 | ○ | `articles[].body` | 600~1,000자, 줄바꿈으로 문단 (FR-02-3 ✅) |
| `conclusion` | 글자 | ○ | `articles[].conclusion` | 한 문장 (FR-02-3 ✅) |
| `words` | 목록 | △ | `articles[].words` | 3~5개 (FR-02-4 ✅) |
| `words[].word` | 글자 | ○ | `words[].word` | 본문에 실제로 있는 글자 |
| `words[].explanation` | 글자 | ○ | `words[].explanation` | 1~2문장, 100자 안팎 |
| `hookLine` | 글자 | ○ | `articles[].hookLine` | 공백 포함 40자 이내 (FR-03-2 ✅) |

```json
{"title": "서울 지하철 노조, 내일 파업 예고",
 "body": "서울 지하철을 운영하는 회사의 노동조합이 내일 아침부터 파업을 하겠다고 밝혔어요.\n…(600~1,000자)…",
 "conclusion": "출근길에는 버스 등 다른 길을 미리 알아 두는 게 좋겠어요.",
 "words": [
   {"word": "노동조합", "explanation": "일하는 사람들이 함께 목소리를 내려고 만든 모임이에요."},
   {"word": "파업", "explanation": "요구를 알리려고 일하는 사람들이 함께 일을 멈추는 거예요."}
 ],
 "hookLine": "내일 아침, 지하철이 멈춘다고?"}
```

- 스크립트가 붙이는 칸(AI가 쓰지 않음): `articleId`·`page`·`order`·`isNotify`·`createdAt`·`carriedFrom`·`sources[]` (06 3-4 ✅).

### 3-4. T4 다른 분야 한 줄 (FR-01-9 ✅ — 8개 분야를 한 번에)

**지시문 전문** — 파일 [`script/prompts/04_other_lines.txt`](../../script/prompts/04_other_lines.txt)

<!-- prompt-file: 04_other_lines.txt -->
```text
너는 한국어 뉴스 앱 "뉴스 봐"의 편집자다.
아래 입력은 여러 분야(category)별 최근 뉴스 검색 결과다. 분야마다 기사 번호(no), 제목(title), 요약(summary)이 있다.

할 일:
- 분야마다 가장 흥미로운 기사를 1개 고른다. 광고·홍보성 기사, 단순 인사·부고, 주가 시세를 나열한 기사는 고르지 않는다.
- 고를 만한 기사가 없는 분야는 빼도 된다.
- 고른 기사마다 어그로 한 줄(hookLine)을 1개 만든다. 규칙:
  - 공백 포함 40자 이내.
  - 그 기사의 제목과 요약에 있는 내용만 토대로 한다.
  - 극단적인 단어(예: "내일", "지금", "죽음", "멸망")와 유행어·친근한 말투를 써도 된다. 단, 너무 자극적이지 않은 선을 지킨다.
  - 과장은 허용한다. 그러나 다음은 절대 쓰지 않는다.
    1) 사실과 정반대인 내용 (예: 살아 있는 사람이 죽었다고 쓰기, 취소된 일을 확정됐다고 쓰기)
    2) 실존 인물을 비난하거나 조롱하는 문장
  - 아래 예시 제목들의 말투를 참고하되, 그대로 베끼지 않는다.

[어그로 예시 제목]
{{HOOK_EXAMPLES}}

출력 규칙:
- 반드시 아래 모양의 JSON 하나만 출력한다. 설명 글이나 코드 블록 표시를 붙이지 않는다.
{"lines": [{"category": "분야 코드", "no": 기사 번호, "hookLine": "..."}, ...]}
- category에는 입력에 있는 분야 코드만 넣는다. 분야마다 최대 1개.
- no에는 그 분야 안에 있는 기사 번호만 넣는다.
```

**입력 예** (사용자가 고르지 않은 큰 분야마다 대표 키워드 1개로 최신순 10개)

```json
{"categories": [
  {"category": "sports", "name": "스포츠",
   "articles": [{"no": 1, "title": "가을야구 끝내기 홈런으로 승부", "summary": "…"},
                {"no": 2, "title": "K리그 시상식 일정", "summary": "…"}]},
  {"category": "life", "name": "생활·건강",
   "articles": [{"no": 1, "title": "독감 백신 무료 접종 시작", "summary": "…"}]}
]}
```

**출력 스키마 → 06 D7 대응**

| AI 칸 | 자료형 | 필수 | 06 필드 | 스크립트가 붙이는 칸 |
|---|---|:---:|---|---|
| `lines[].category` | 글자 (큰 분야 코드) | ○ | `otherLines[].category` | — |
| `lines[].no` | 정수 | ○ | (그 분야 기사 번호) | `articleTitle`·`url`·`linkType`·`press`·`publishedAt` |
| `lines[].hookLine` | 글자 | ○ | `otherLines[].hookLine` | — |

```json
{"lines": [
  {"category": "sports", "no": 1, "hookLine": "경기 종료 직전, 야구장이 뒤집혔다"},
  {"category": "life", "no": 1, "hookLine": "지금 안 맞으면 손해? 독감 백신 무료 시작"}
]}
```

### 3-5. T5 알림용 한 줄 고르기 (FR-04-2 ✅)

**지시문 전문** — 파일 [`script/prompts/05_pick_notify.txt`](../../script/prompts/05_pick_notify.txt)

<!-- prompt-file: 05_pick_notify.txt -->
```text
너는 한국어 뉴스 앱 "뉴스 봐"의 편집자다.
아래 입력은 이번 회차에 새로 만든 종합 기사 목록이다. 각 기사에는 번호(no), 어그로 한 줄(hookLine), 종합 기사 제목(title), 원문 기사 수(sourceCount)가 있다.

할 일:
- 휴대폰 알림으로 딱 1개만 보낸다면, 가장 눌러 보고 싶게 만드는(또는 기사 내용이 가장 풍부한) 것을 1개 고른다.
- 어그로 한 줄이 아무리 흥미로워도 종합 기사 제목과 내용이 동떨어진 것은 고르지 않는다.

출력 규칙:
- 반드시 아래 모양의 JSON 하나만 출력한다. 설명 글이나 코드 블록 표시를 붙이지 않는다.
{"picked": 기사 번호, "reason": "고른 이유 한 문장"}
- picked에는 입력에 있는 번호(no) 1개만 넣는다.
```

**입력 예** (이번 회차에 **새로 만든** 기사만 — 직전 회차에서 복사한 기사는 제외, 06 3-3 ✅)

```json
{"articles": [
  {"no": 1, "hookLine": "내일 아침, 지하철이 멈춘다고?", "title": "서울 지하철 노조, 내일 파업 예고", "sourceCount": 5},
  {"no": 2, "hookLine": "달까지 간 우리 우주선, 다음은?", "title": "한국 우주선 달 궤도 진입", "sourceCount": 2}
]}
```

**출력 스키마**

| 칸 | 자료형 | 필수 | 뜻 → 06 |
|---|---|:---:|---|
| `picked` | 정수 | ○ | 고른 기사 번호 → 그 기사 `isNotify: true`, 회차 `notifyArticleId` = 그 `articleId` |
| `reason` | 글자 | △ | 실행 로그용 |

```json
{"picked": 1, "reason": "내일 출근길에 바로 영향이 있어 가장 눌러 보고 싶음"}
```

### 3-6. 어그로 예시 제목 15개 — ⚠ 초안 (사용자가 교체 예정)

> 기능명세서 FR-03-1 ✅ 확정 사항은 **"예시 제목은 사용자가 직접 15개 골라 글 파일에 적는다"** 입니다. 아래 15개는 시험 실행을 위해 작성자가 **지어낸 초안**이며 실제 기사 제목이 아닙니다. **사용자가 직접 고른 15개로 바꿔 주세요.** 바꾼 뒤에는 이 문서의 아래 블록도 같은 내용으로 고쳐야 단위 시험이 통과합니다.

**전문** — 파일 [`script/prompts/hook_examples.txt`](../../script/prompts/hook_examples.txt) (`#` 줄은 스크립트가 읽지 않는 메모)

<!-- prompt-file: hook_examples.txt -->
```text
# [초안 - 사용자가 교체 예정] 어그로 한 줄 예시 제목 15개 (FR-03-1)
# 원래 확정 사항: "예시 제목은 사용자가 직접 15개 골라 이 파일에 적는다" (03 기능명세서 FR-03-1).
# 아래 15개는 시험 실행을 위해 작성자(advlab-backend)가 지어낸 초안입니다. 실제 기사 제목이 아닙니다.
# 규칙: 한 줄에 제목 1개. '#'으로 시작하는 줄과 빈 줄은 스크립트가 읽지 않습니다.
내일부터 지갑이 얇아진다? 다음 달 바뀌는 것들
지금 안 보면 손해… 월급날 전에 꼭 알아야 할 금리 소식
공룡 멸망급 충격? 하늘에서 떨어진 돌 하나의 정체
이거 실화? 편의점 도시락 값이 또 올랐다
스마트폰 배터리, 이렇게 쓰면 수명 반토막
지구 온도 1.5도, 이제 진짜 한계선이 코앞
우주에서 온 신호? 과학자들이 밤잠 설친 이유
출근길 대란 예고… 내일 아침 지하철 어쩌나
반도체 전쟁 2라운드, 우리나라 성적표는?
집값 바닥 찍었다? 전문가들 의견 완전 갈렸다
AI가 내 일자리 가져간다고? 진짜 사라지는 직업
역대급 폭염 다음은 역대급 한파? 올겨울 날씨 미리보기
경기 종료 3초 전, 경기장이 뒤집혔다
이 과일, 알고 보니 멸종 위기라고?
오늘 밤 하늘 놓치면 100년 기다려야 한다
```

---

## 4. AI 결과 검사 규칙 (스크립트 `ai_tasks.py`)

> AI 답을 그대로 믿지 않고, 저장 전에 아래 규칙으로 고치거나 버립니다. "실패"면 [5장](#5-에러코드오류-처리) 처리로 넘어갑니다. 모든 규칙은 가짜 응답으로 단위 시험했습니다([7-3](#7-3-단위-시험-결과)).

### 4-1. 공통

| # | 규칙 | 결과 | 근거 |
|:---:|---|---|---|
| C1 | 답이 JSON이 아님 / JSON이지만 `{...}`(객체)가 아님 | **실패** | FR-02-3 예외 ✅ |
| C2 | 답이 ```` ```json … ``` ```` 로 감싸져 오면 감싼 표시만 벗기고 읽음 | 통과 | ✅ 추천대로 |
| C3 | 번호 칸(`picked`·`items`·`no`)에 입력에 없는 번호·중복·참거짓 값 | 그 값만 버림 | ✅ 추천대로 |

### 4-2. T3 종합 기사 (가장 중요)

| # | 규칙 | 결과 | 근거 |
|:---:|---|---|---|
| A1 | `title`·`body`·`conclusion` 중 하나라도 비어 있음 | **실패** | FR-02-3 완료 기준 ✅ "제목·본문·결론이 모두 있다" |
| A2 | 본문이 **300자 미만** | **실패** | ✅ 추천대로 (신규 — 너무 짧으면 종합 기사가 아님) |
| A3 | 본문이 300~599자 또는 1,000자 초과 | 통과 + 경고 `BODY_LENGTH` | FR-02-3 ✅ 600~1,000자 / 버리면 기사가 줄어 SLO-03에 불리 → 경고만 (✅ 추천대로, 신규) |
| A4 | **원문과 같은 글자가 50자 이상 이어짐** (공백·줄바꿈은 무시하고 비교) | **실패** | FR-02-3 완료 기준 ✅ "50자 이상 그대로 들어 있지 않다", NFR-08 |
| A5 | `words` 중 **본문에 없는 단어** | 그 단어 버림 | FR-02-4 예외 ✅ |
| A6 | `words` 중 같은 단어 두 번 / 단어·해설 빈 값 | 버림 | ✅ 추천대로 |
| A7 | `words`를 본문에 처음 나오는 순서로 정렬, **최대 5개** | — | 06 3-5 ✅, FR-02-4 ✅ |
| A8 | `words`가 0개이거나 목록이 아님 | 통과 (빈 목록) | FR-02-4 예외 ✅ "0개여도 정상" |
| A9 | `hookLine` 연속 공백·줄바꿈을 한 칸 띄어쓰기로 | — | ✅ 추천대로 |
| A10 | `hookLine`이 비었음 | **종합 기사 제목으로 대신** | FR-03-2 예외 ✅ |
| A11 | `hookLine`이 공백 포함 **40자 초과** | **앞 40자 + "…"** | FR-03-2 예외 ✅ |

- A4 "50자 복사" 검사 방법: 원문(추출 본문·요약)에서 공백을 지운 뒤 50글자짜리 조각을 모두 모아 두고, 종합 기사 본문(공백 지움)의 50글자 조각이 그 안에 하나라도 있으면 복사로 봅니다. 기사 5개 × 3,000자여도 순식간에 끝납니다.
- 금지 규칙(사실과 정반대·실존 인물 비난, FR-03-1 ✅)은 **지시문으로만** 막습니다. 글자 검사로 판단할 수 없기 때문입니다 (기획서 3-2 ✅ "환각 별도 대책 없음"과 같은 태도).

### 4-3. T1·T2·T4·T5

| 작업 | 규칙 | 결과 |
|---|---|---|
| T1 | `picked`에서 쓸 수 있는 번호가 0개 | **실패** → 위에서 3개 |
| T1 | 4개 이상 | 앞 3개만 (03 v1.3 ✅) |
| T2 | `groups`가 목록이 아님 / 쓸 수 있는 묶음 0개 | **실패** → 최신순 1개씩 |
| T2 | 한 묶음 6개 이상 | 앞 5개만 (FR-02-1 ✅) |
| T2 | 같은 기사가 여러 묶음에 | 처음 묶음에만 남김 |
| T2 | `picked`가 비었거나 모두 틀림 | 묶음은 쓰고, 고르기만 위에서 3개 (`PICK_FALLBACK`) |
| T4 | `lines`가 목록이 아님 | **실패** → 칸 숨김 |
| T4 | 입력에 없는 분야, 같은 분야 두 번, 틀린 기사 번호 | 그 줄만 버림 |
| T4 | `hookLine` 규칙 | T3의 A9~A11과 같음 (빈 값이면 **원문 기사 제목**으로) |
| T4 | 저장 순서 | 큰 분야 코드표 순서 (06 3-7 ✅) |
| T5 | `picked`가 입력 범위 밖 / 정수 아님 | **실패** → 원문 기사 수 최다 기사 |

---

## 5. 에러코드·오류 처리

### 5-1. 다시 시도 규칙 (FR-02-3 ✅ "1번만 다시 시도")

| 작업 | 실패로 보는 것 | 다시 시도 | 최대 호출 |
|---|---|---|:---:|
| T3 | 호출 오류(네트워크·429·500 등) **또는** JSON 아님 **또는** 4-2의 "실패" | 합쳐서 **1번** | 2 |
| T1·T2·T4·T5 | 호출 오류 또는 JSON 아님 | 1번 | 2 |
| T1·T2·T4·T5 | JSON은 맞지만 4-3의 "실패" | 다시 시도 **안 함** → 바로 대체 동작 | 1 |

- T3만 검사 실패도 다시 시도하는 이유: 종합 기사는 서비스의 본체(기획서 1-5 원칙 1 ✅)이고, 복사·빈 값은 다시 쓰면 나아질 가능성이 큽니다. 나머지는 대체 동작이 이미 정해져 있어 호출을 아낍니다(✅ 추천대로).
- 최악의 경우 회차당 호출: T1 2 + T2 4 + T3 18 + T4 2 + T5 2 = **28번**, 하루 84번 → NFR-05(하루 50번 이하)를 넘을 수 있습니다. 보통은 14번 × 3 = 42번입니다. [9장](#9-앞-문서와-어긋나거나-이-문서에서-새로-정한-것) 참고.

### 5-2. 바깥 창구 오류 → 우리 처리 (경고 코드는 06 4-6 ✅)

| 창구 | 오류 | 공식 코드 (🔍) | 우리 처리 | 경고 코드 |
|---|---|---|---|---|
| A1 | 응답 없음·HTTP 오류·빈 목록 | — | 오늘의 화제 이번 회차 건너뜀, 직전 회차 유지 (FR-01-4 ✅) | `PAGE_SKIPPED` |
| A1' | 해독 실패·예외 | `success: false` | 구글 링크 그대로, 추출 `not_tried` (ADR-007 ✅) | `GOOGLE_DECODE_LOW` (성공/시도) |
| A2 | 잘못된 요청 | `SE01`·`SE02`·`SE03`·`SE04`·`SE06` (HTTP 400) | 그 페이지 건너뜀, 직전 회차 유지 (FR-01-5 ✅) | `PAGE_SKIPPED` |
| A2 | 주소 오타 | `SE05` (404) | 같음 | `PAGE_SKIPPED` |
| A2 | 네이버 서버 오류 | `SE99` (500) | 같음 | `PAGE_SKIPPED` |
| A2 | 권한 없음 (앱 설정에서 "검색" 미선택) | HTTP 403 | 같음 + README에 해결 방법 | `PAGE_SKIPPED` |
| A2 | 24시간 안 기사로 묶음 0개 | — | 48시간으로 한 번 넓힘 (FR-01-5 ✅) | `WINDOW_48H` |
| A3 | 열기 실패·10초·200자 미만·빈 값 | — | 요약으로 / 오늘의 화제는 제목만 (FR-02-2 ✅) | 기사별 `extractResult`, 묶음 전체면 `TITLE_ONLY` |
| A3 | 오늘의 화제 묶음이 제목 1개뿐이고 본문 없음 | — | 그 묶음 건너뛰고 다음 순서 후보 (FR-02-2 ✅) | `AI_GROUP_SKIPPED` |
| A4 | 키 없음 | — | **시험판**: 안내 글을 보여주고 모으기·추출 결과만 저장 후 종료(종료 코드 2) | `AI_KEY_MISSING` (시험판 전용, 신규) |
| A4 | 한도 초과·서버 오류·JSON 아님 | HTTP 429 / 500·503 / — (SDK가 `APIError`로 알림) | 5-1 다시 시도 → 작업별 대체 동작 | `AI_GROUP_SKIPPED`·`PICK_FALLBACK`·`GROUP_FALLBACK`·`OTHER_LINES_HIDDEN`·`NOTIFY_FALLBACK` |
| A4 | T3 본문 길이 범위 밖(실패 아님) | — | 그대로 저장 | `BODY_LENGTH` (신규) |
| A5 | 저장 오류 | — | 실행 실패, GitHub 실패 메일 (FR-02-6 ✅) | `status: failed` |

- 오류 글(`errorMessage`·경고 `detail`)에는 **키를 절대 넣지 않습니다.** `ai_client.py`는 오류 글에 키 글자가 섞이면 `***`로 바꿔 지웁니다 (NFR-06 ✅).

---

## 6. 인증·권한

| 창구 | 인증 방법 | 키를 어디에 두나 | 코드에서 읽는 곳 | 근거 |
|---|---|---|---|---|
| A1·A1'·A3 | 없음 | — | — | 03 8장 ✅ |
| A2 | 요청 머리글 `X-Naver-Client-Id`, `X-Naver-Client-Secret` (🔍 공식). 네이버 개발자 센터에서 앱 등록 시 **"검색" API를 골라야** 함 (아니면 403) | 운영: GitHub Secrets / 시험: PowerShell 환경변수 `NAVER_CLIENT_ID`·`NAVER_CLIENT_SECRET` | `collect.naver_keys()` | NFR-06 ✅ |
| A4 | Gemini API 키 (Google AI Studio에서 발급, 카드 등록 없음) | 운영: GitHub Secrets / 시험: 환경변수 `GEMINI_API_KEY` | `ai_client.py` **한 곳만** | NFR-06 ✅, ADR-008 ✅ |
| A5 | Firebase 서비스 계정 열쇠 | GitHub Secrets `FIREBASE_SERVICE_ACCOUNT_JSON` | `settings_store.py` (운영판) | 08 6장 ✅, [09](09_보안_개인정보.md) |
| A6 | 익명 로그인 + 주인 UID 보안 규칙 | 앱 (키 없음) | 앱 | 08 6장 ✅, [09](09_보안_개인정보.md) |

- **키를 코드·파일·로그에 쓰지 않습니다.** 시험판도 환경변수에서만 읽고, 결과 파일에는 "키 있음/없음"(참·거짓)만 남깁니다.
- AI(A4)에는 **공개 뉴스 기사(제목·본문 일부·요약)만** 보냅니다. 사용자 분야 선택 등 개인과 이어지는 정보는 보내지 않습니다 — T2 입력의 `field`는 분야 이름(예 "과학")뿐입니다 (NFR-07 ✅). 무료 요금제는 보낸 내용이 구글 제품 개선에 쓰입니다(🔍 요금 페이지 "Used to improve our products: Yes").

---

## 7. 시험 실행 결과 (2026-10-28)

### 7-1. 실행한 것과 실행하지 않은 것

| 단계 | 실제 실행 | 이유 |
|---|:---:|---|
| 가상환경 만들기·부품 설치 (`requirements.txt` 버전 고정) | ✅ | — |
| A1 구글 RSS 모으기 | ✅ | 키 불필요 |
| A1' 구글 링크 → 원문 주소 | ✅ | 키 불필요 |
| A3 본문 추출 | ✅ | 키 불필요 |
| A2 네이버 검색 | ❌ | 네이버 키 없음 → 스크립트가 "건너뜀" 메모를 남기는 것까지 확인 |
| A4 Gemini (T1~T5) | ❌ | Gemini 키 없음 → **안내 글 출력 후 종료(코드 2)** 확인. 결과 검사는 가짜 응답으로 단위 시험 |

### 7-2. 실제 실행 결과 (`script/sample_output/run_20261028-1618.*`)

| 항목 | 값 (결과 파일에서 그대로) |
|---|---|
| 실행 명령 | `.\.venv\Scripts\python.exe main.py` (Gemini·네이버 키 없음) |
| 종료 코드 | 2 (키 없음 안내 후 종료) |
| 상태 `status` | `no_result` |
| 후보 묶음 (A1 위에서 5개) | 5개, 원문 기사 25개 |
| 고른 묶음 (키 없음 → 위에서 3개) | 3개, 원문 기사 15개 |
| 링크 해독 `googleDecode` | 15/15 성공 (100%) |
| 본문 추출 `extract` | 11/15 성공 (73%) — 결과 코드별: `empty` 2, `ok` 11, `too_short` 2 |
| AI 호출 수 `aiCalls` | 0 |
| 걸린 시간 — 1 오늘의 화제 RSS 모으기 | 1.26초 |
| 걸린 시간 — 2 오늘의 화제 고르기(AI T1) | 0.0초 |
| 걸린 시간 — 4 구글 링크 해독 + 본문 추출 | 57.09초 |
| 걸린 시간 — 전체 `durationSec` | 58.35초 |
| 경고 | `AI_KEY_MISSING` |

- 같은 날 16:26 **두 번째 실행**(`run_20261028-1626.*`, 검증 기록에 출력 원문): 후보 5묶음·25기사, 링크 해독 **15/15**, 본문 추출 **12/15**, 전체 **57.66초**. 그사이 뉴스 순서가 바뀌어 첫 묶음이 달랐습니다. 두 번 모두 해독 100%, 추출 73~80%.

- 추출 실패 4건의 내용: `empty` 2건(2건 모두 같은 언론사 사이트 — 본문을 웹페이지가 열린 뒤 따로 불러오는 방식으로 추정, ❓ 원인 미확인), `too_short` 2건(사진 기사·포토 페이지). 실패한 기사는 FR-02-2 ✅대로 같은 묶음의 다른 기사 본문으로 보충됩니다(묶음 3개 모두 본문 1개 이상 확보).
- 걸린 시간 대부분은 링크 해독(요청 사이 1초 쉼)과 원문 사이트 응답입니다. 회차 전체 예상: 오늘의 화제 약 1분 + 관심·추천 각 수십 초 + AI 최대 14번 × 약 5초 ≈ **3~4분** → NFR-01(25분 안) 여유 있음 (AI 시간은 ⏳ 키 발급 후 실측).

### 7-3. 단위 시험 결과

| 항목 | 값 |
|---|---|
| 실행 명령 | `.\.venv\Scripts\python.exe -m unittest discover -s tests -v` (Gemini 키 없이, 인터넷 없이) |
| 결과 (unittest 마지막 줄 그대로) | `Ran 38 tests in 0.091s` / `OK` |
| 시험 파일 | [`script/tests/test_ai_tasks.py`](../../script/tests/test_ai_tasks.py) (검사 규칙·재시도·지시문 파일과 문서 일치), [`script/tests/test_flow.py`](../../script/tests/test_flow.py) (RSS 목록 읽기·네이버 글자 정리·24시간 거르기, 가짜 AI로 전체 흐름·키 없음 종료, **결과 파일에 원문 본문이 없는지**) |
| 검증 기록 | `artifacts/verify_api07.txt` (명령 출력 원문) |

---

## 8. 기능(FR) ↔ 창구 ↔ AI 작업 추적표

> [INDEX·추적표](01_INDEX_RTM.md)(🔴 미작성)의 "API" 열에 **등재 예정**인 원본입니다.

| FR | 이름 | 창구 | AI 작업 | 코드 | 검사·시험 |
|---|---|---|---|---|---|
| FR-01-2 | 선택한 분야 저장 | A5(읽기)·A6(쓰기) | — | `settings_store.py`(운영판) | — |
| FR-01-4 | 오늘의 화제 모으기 | A1, A1' | T1 | `collect.py`, `google_link.py` | `TestCollectHelpers`, 실제 실행 7-2 |
| FR-01-5 | 나의 관심 분야 모으기 | A2 | T2 | `collect.py` | `TestCollectHelpers` (⏳ 실제 호출) |
| FR-01-6 | 추천 뉴스 모으기 | A2 | T2 | (운영판) | ⏳ |
| FR-01-7 | 3개 페이지 표시 | A6 | — | 앱 | — |
| FR-01-9 | 다른 분야 한 줄 | A2 | T4 | `main.py --other-lines` | `test_other_lines` |
| FR-02-1 | 같은 사건 묶기 | — | T2 | `ai_tasks.validate_groups` | `test_groups*` |
| FR-02-2 | 원문 본문 추출 | A3 | — | `extract.py` | 실제 실행 7-2 |
| FR-02-3 | 종합 기사 작성 | A4 | T3 | `ai_tasks.validate_article` | `TestValidateArticle`, `TestCopyCheck`, `TestTasksRetry` |
| FR-02-4 | 어려운 단어 해설 | A4 | T3 | 같음 | `test_ok_and_rules`, `test_words_max_5` |
| FR-02-5 | 출처 링크 | A1'·A2 | — | `main.build_article` | `test_with_fake_ai` |
| FR-02-6 | 처리 결과 저장 | A5 | — | `main.save` (시험판: 파일) | `test_with_fake_ai`, `test_without_key_stops_kindly` |
| FR-03-1 | 어그로 지시문(규칙+예시) | — | T3·T4 | `prompts/`, `ai_tasks.load_prompt` | `test_placeholder_filled`, `test_examples_draft_15`, `TestDocMatchesPromptFiles` |
| FR-03-2 | 어그로 한 줄 생성 | A4 | T3 | `ai_tasks.cut_hook` | `TestHook` |
| FR-04-2 | 알림용 한 줄 고르기 | A4, A6 | T5 | `ai_tasks.validate_notify` | `test_notify`, `test_with_fake_ai` |

---

## 9. 앞 문서와 어긋나거나 이 문서에서 새로 정한 것

### 9-1. 앞 문서와 어긋나는 것 (앞 문서 고침 필요 — 이 문서에서는 고치지 않음)

| # | 문서·위치 | 지금 적힌 내용 | 확인된 사실 / 고칠 내용 |
|:---:|---|---|---|
| D1 | [02](02_기획서.md) 5-4 "한도" | "외부 자료 기준 Flash-Lite는 하루 약 500회 (Flash는 약 20회)" — 출처·모델 이름 없음 | 공식 문서(rate limit, 2026-10-26 갱신)는 무료 한도 숫자를 **싣지 않고 AI Studio 화면에서만** 보여 줌. 500회는 비공식 정리글(2026-07-11)의 **Gemini 3.1 Flash-Lite 500 RPD·15 RPM** 숫자. → "공식 문서에 숫자 없음, AI Studio 화면 확인값 기록. 참고: 비공식 자료 3.1 Flash-Lite 500 RPD(2026-07)"로 고치고 출처 URL 추가 |
| D2 | 02 5-4 "결정" · 03 FR-02-3 · 08 ADR-002 | "Flash-Lite 모델" (정확한 모델 이름 없음) | 정확한 모델 이름 **`gemini-3.1-flash-lite`**(기본값, 안정판·무료) 명시. 교체 후보 `gemini-3.5-flash-lite`. `gemini-2.0-flash-lite`·`3.1-flash-lite-preview`는 서비스 종료 |
| D3 | [03](03_기능명세서.md) FR-02-1 아래 ⚠ 상자 | "Flash-Lite 무료 한도(외부 자료 기준 하루 약 500회)" | D1과 같이 고침 |
| D4 | 02 5-4 "사용량" | "하루 약 33번" | 03 NFR-05 v1.4 계산은 **최대 약 42번**(이 문서 1-2와 같음). 재시도까지 최악이면 84번(5-1) |
| D5 | [06](06_데이터모델_ERD.md) 3-6 ⚠ | "네이버 응답에 언론사 항목이 없다고 알려짐, 공식 확인 못 함, 07에서 결정" | 🔍 공식 확인: **없음**. → `press` = 원문 주소 도메인(`www.`·`m.` 제거)으로 결정(2-3). 06의 ⚠를 해결로 바꿈 |
| D6 | 06 4-6 경고 코드 표 | 11개 | 새 경고 `BODY_LENGTH`(본문 길이 범위 밖, 4-2 A3) 추가 필요. `AI_KEY_MISSING`은 시험판 전용이라 06에는 안 넣어도 됨 |
| D7 | [08](08_아키텍처_ADR.md) ADR-007 "확인하지 못한 것 ③ 성공률" | 실측 필요 | 🔍 2026-10-28 2회 실측 모두 **15/15 성공**(표본 2회, 같은 날). 응답 키는 `success`(부품 0.2.2) |
| D8 | 08 ADR-011 | 부품 이름만, 버전 미기재 ("구현 시점에 다시 확인") | 확인한 버전: google-genai 2.33.0 · googlenewsdecoder 0.2.2 · trafilatura 2.3.1 · feedparser 6.0.14 · requests 2.34.2 · firebase-admin 7.7.0. **googlenewsdecoder는 파이썬 3.11 이상** → GitHub Actions 파이썬 버전을 3.11 이상으로 (11 운영·배포에 반영) |
| D9 | 08 4장 A4 "하루 한도·분당 한도 모두 AI Studio에서 확인" | — | 맞음(공식 확인). 분당 한도 대비로 호출 간격 4.5초를 두는 것을 추가 |

### 9-2. 이 문서에서 새로 정한 것 (✅ 추천대로 — 모두 설정값·코드 한 곳이라 쉽게 고침)

| # | 정한 것 | 위치 |
|:---:|---|---|
| N1 | AI 작업 번호 T1~T5, 지시문 파일 이름 5개 | 1-2 |
| N2 | 기본 모델 `gemini-3.1-flash-lite`, 환경변수 `GEMINI_MODEL`로 교체 | 1-3 ③ |
| N3 | AI 호출 사이 최소 4.5초 | 1-3 ②, 2-5 |
| N4 | AI 출력 JSON 칸 이름 = 06 필드 이름. 기사는 번호(`no`)로만 가리키고 링크·언론사는 스크립트가 붙임 | 3장 원칙 |
| N5 | `response_json_schema`(스키마 강제)는 쓰지 않고 지시문 + 스크립트 검사로 | 2-5 |
| N6 | 본문 300자 미만 = 실패, 300~599자·1,000자 초과 = 경고만(`BODY_LENGTH`) | 4-2 A2·A3 |
| N7 | 50자 복사 검사는 공백을 지우고 비교, 복사면 T3 실패 → 다시 시도 | 4-2 A4, 5-1 |
| N8 | 다시 시도 규칙: T3는 검사 실패까지 합쳐 1번, 나머지는 호출 오류·JSON 아님만 1번 | 5-1 |
| N9 | 네이버 `press` = 도메인 | 2-3 |
| N10 | 단어 해설 빈 값·중복 제거 | 4-2 A6 |
| N11 | 어그로 예시 제목 **초안 15개** (사용자가 교체 예정) | 3-6 |
| N12 | 시험판 전용: 경고 `AI_KEY_MISSING`, 종료 코드 2, 관심 분야 기사는 AI에 최대 40개만 보냄 | 5-2, `script/main.py` |

### 9-3. 사용자 확인이 필요한 것

| # | 질문 | 추천 |
|:---:|---|---|
| Q1 | 어그로 예시 제목 15개를 직접 골라 `script/prompts/hook_examples.txt`(와 이 문서 3-6)를 바꿔 주세요 (FR-03-1 ✅ 원래 사용자 몫) | — |
| Q2 | Gemini 키를 발급받아 AI Studio 한도 화면에서 `gemini-3.1-flash-lite`·`gemini-3.5-flash-lite`의 RPM·RPD를 확인해 주세요. 그 값으로 02 5-4를 고칩니다 | 3.5 Flash-Lite가 50 RPD 이상이면 3.5로 교체 고려 |
| Q3 | 최악의 경우 하루 84번 호출로 NFR-05(50번)를 넘을 수 있습니다. NFR-05를 "보통 42번, 재시도 포함 최대 약 84번(무료 한도 안)"으로 고칠까요, 아니면 재시도를 줄일까요? | NFR-05 문구 수정 (한도 500 RPD가 맞으면 충분) |

---

## 변경이력

| 일자 | 버전 | 변경 내용 |
|---|---|---|
| 2026-10-28 | v1.0 | 신규 작성 (advlab-backend). A1~A6 요청·응답 형식, AI 작업 T1~T5 지시문 전문·입출력 스키마·검사 규칙·오류 처리, 최신 사실 확인(모델 이름·무료 한도 출처·네이버 공식 문서·부품 버전), 시험 실행 결과, 앞 문서 수정 필요 목록. 어그로 예시 제목은 초안(사용자 교체 예정) |
