# 뉴스 봐 - 시험 실행 스크립트 (`script/`)

| 항목 | 내용 |
|---|---|
| 무엇 | 서버 쪽 처리(모으기 → 원문 주소 → 본문 추출 → AI 정리 → 알림용 고르기)를 **내 컴퓨터에서 한 번** 돌려 보는 시험판 |
| 근거 | [API 명세서](../docs/design/07_API명세서.md) · [아키텍처 ADR-007~009·011](../docs/design/08_아키텍처_ADR.md) · [기능명세서](../docs/design/03_기능명세서.md) |
| 운영판과 다른 점 | Firestore 를 쓰지 않음(결과는 `sample_output/` 파일로), 추천 뉴스 탭 없음, 관심 분야는 네이버 키가 있을 때 1개만 |
| 기준 환경 | Windows 11 + PowerShell, 파이썬 3.11 이상 (확인한 버전: 3.13.2) |

> 약어: **API**(Application Programming Interface, 프로그램끼리 데이터를 주고받는 창구) · **RSS**(새 글 목록을 정해진 형식으로 내보내는 방식) · **JSON**("이름: 값" 형태의 데이터 글자 형식) · **RPM/RPD**(분당/하루 요청 수 한도)

## 1. 처음 한 번만 - 설치

PowerShell 을 열고 이 폴더로 이동한 뒤:

```powershell
cd C:\Users\Sonyul\adventure_design\script
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

- `.venv` 는 이 프로젝트 전용 파이썬 부품 상자(가상환경)입니다. 컴퓨터 전체에는 아무것도 설치되지 않습니다.
- 부품 버전은 `requirements.txt` 에 고정돼 있습니다 (2026-10-28 PyPI 기준 최신).

## 2. 키 발급 (무료)

### 2-1. Gemini API 키 (필수 - AI 단계)

1. <https://aistudio.google.com/apikey> 에 구글 계정으로 들어갑니다.
2. **Create API key**(키 만들기)를 누릅니다. 카드 등록은 필요 없습니다.
3. 나온 키를 복사합니다. **이 키는 비밀번호처럼 다룹니다** - 파일·코드·카톡·과제 문서에 붙여 넣지 마세요.
4. 무료 한도(분당·하루 호출 수)는 <https://aistudio.google.com/rate-limit> 화면에서 내 프로젝트 기준으로 확인합니다. 공식 문서에는 무료 한도 숫자가 적혀 있지 않습니다(07 명세서 1-3).

### 2-2. 네이버 검색 API 키 (선택 - "나의 관심 분야" 시험)

1. <https://developers.naver.com/apps/#/register> 에서 애플리케이션 등록.
2. **사용 API** 에서 **검색** 을 고릅니다. 환경은 "WEB 설정"에 `http://localhost` 를 넣으면 됩니다.
3. 등록 후 **Client ID** 와 **Client Secret** 을 확인합니다. (하루 25,000회 무료)

## 3. 실행

키는 **환경변수**로만 넣습니다. 아래처럼 넣으면 그 PowerShell 창을 닫을 때 사라집니다(안전).

```powershell
cd C:\Users\Sonyul\adventure_design\script
$env:GEMINI_API_KEY = "여기에_Gemini_키"
# (선택) 네이버
$env:NAVER_CLIENT_ID = "여기에_Client_ID"
$env:NAVER_CLIENT_SECRET = "여기에_Client_Secret"

.\.venv\Scripts\python.exe main.py
```

| 선택 옵션 | 뜻 |
|---|---|
| `--max-groups 1` | 오늘의 화제 묶음을 최대 1개만 (AI 호출을 아끼고 싶을 때, 기본 3) |
| `--no-naver` | 네이버 키가 있어도 관심 분야를 건너뜀 |
| `--other-lines` | "다른 분야 한 줄"(FR-01-9)도 시도 (네이버 키 필요, 네이버 검색 8번 + AI 1번 추가) |

다른 모델로 바꿔 보기 (교체 가능 구조, NFR-09):

```powershell
$env:GEMINI_MODEL = "gemini-3.5-flash-lite"
.\.venv\Scripts\python.exe main.py
```

시험용 분야를 바꾸려면 `TRIAL_FIRST_CATEGORY`, `TRIAL_DEEP_CATEGORY`, `TRIAL_SECOND_CATEGORY` 환경변수에 [데이터 모델 4-8](../docs/design/06_데이터모델_ERD.md) 의 코드(예: `it`, `it_ai`, `science`)를 넣습니다. 기본은 과학 → 우주 / 2순위 경제.

### 결과 보기

- `sample_output/run_YYYYMMDD-HHmm.md` : 사람이 읽기 쉬운 결과 (종합 기사, 단어 해설, 어그로 한 줄, 출처, 단계별 걸린 시간)
- `sample_output/run_YYYYMMDD-HHmm.json` : 데이터 모델(06)의 `runs`·`editions` 모양 그대로 + 시험용 칸(`stepTimingsSec`, `collected`)
- **원문 기사 본문은 저장하지 않습니다**(NFR-08). 추출한 글자 **수**만 남깁니다.

### 종료 코드

| 코드 | 뜻 |
|:---:|---|
| 0 | 끝까지 완료 |
| 2 | Gemini 키가 없어 AI 단계 전에 멈춤 (모으기·링크 해독·본문 추출 결과는 저장됨) |
| 1 | 그 밖의 오류 |

## 4. 시험(테스트) 돌리기 - 키·인터넷 없이

```powershell
cd C:\Users\Sonyul\adventure_design\script
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

- 가짜 AI 응답으로 결과 검사 규칙(40자 자르기, 본문에 없는 단어 버리기, 50자 이상 원문 복사 금지, JSON 아님 → 실패, 1번 재시도)을 확인합니다.
- `07_API명세서.md` 에 실린 지시문 전문이 `prompts/` 파일과 글자 하나까지 같은지도 확인합니다.

## 5. 파일 구성 (08 ADR-009 를 따름)

| 파일 | 하는 일 |
|---|---|
| `main.py` | 처리 순서대로 부르기, 단계별 걸린 시간·AI 호출 수·추출 성공 수 기록, 결과 저장 |
| `config.py` | 숫자(40자·600~1,000자·10초 등), 분야·키워드 목록, AI 모델 이름 |
| `collect.py` | A1 구글 뉴스 RSS, A2 네이버 뉴스 검색 |
| `google_link.py` | 구글 뉴스 링크 → 원문 주소 (`googlenewsdecoder`) |
| `extract.py` | A3 본문 추출 (`trafilatura`), 실패 판정 |
| `ai_client.py` | A4 Gemini 호출 창구 1곳 (키는 환경변수에서만) |
| `ai_tasks.py` | AI 작업 T1~T5 와 결과 검사 |
| `prompts/` | 지시문 5개 + 어그로 예시 제목 15개(**초안 - 사용자가 교체 예정**) |
| `tests/` | 단위 시험 |

## 6. 주의

- `prompts/hook_examples.txt` 의 15개는 **작성자가 만든 초안**입니다. 기능명세서 FR-03-1 확정 사항대로 **사용자가 직접 고른 15개로 바꿔 주세요.**
- 구글 뉴스 링크 해독 부품은 구글이 방식을 바꾸면 갑자기 실패할 수 있습니다. 실패하면 구글 링크를 그대로 두고 그 기사는 본문 추출을 건너뜁니다(ADR-007).
- 이 폴더를 공개 저장소에 올릴 때 `sample_output/` 결과 파일은 `.gitignore` 로 빠집니다.
