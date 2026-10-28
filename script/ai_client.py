"""AI 호출 창구 1곳 (08 ADR-008 `ai_client.py`, NFR-09).

"지시문(system) + 입력(JSON)을 주면 JSON(dict)을 돌려주는" 함수 하나만 바깥에 보인다.
다른 파일은 AI 회사 이름을 모른다. 다른 AI로 바꿀 때는 이 파일의 _call_gemini 만 다시 쓴다.

키 규칙 (NFR-06): 키는 환경변수 GEMINI_API_KEY 에서만 읽고, 코드·파일·로그에 쓰지 않는다.
"""
from __future__ import annotations

import json
import os
import time

import config


class AiError(Exception):
    """AI 호출 실패 (오류·한도 초과·JSON 아님). 호출한 쪽은 '그 묶음 건너뛰기' 등으로 처리."""


class AiKeyMissing(AiError):
    """GEMINI_API_KEY 환경변수가 없음."""


KEY_HELP = (
    "Gemini API 키가 없어 AI 단계를 건너뜁니다.\n"
    "  1) https://aistudio.google.com/apikey 에서 구글 계정으로 키를 발급받으세요 (무료, 카드 등록 없음).\n"
    "  2) PowerShell 에서:  $env:GEMINI_API_KEY = \"발급받은_키\"\n"
    "  3) 다시 실행:        .\\.venv\\Scripts\\python.exe main.py\n"
    "  (키는 이 창을 닫으면 사라집니다. 파일·코드에 적지 마세요.)"
)


class AiClient:
    def __init__(self) -> None:
        self.calls = 0            # 재시도 포함 실제 호출 수 (D2 aiCalls, NFR-05)
        self._last_call = 0.0
        self._client = None

    @staticmethod
    def has_key() -> bool:
        return bool(os.environ.get("GEMINI_API_KEY", "").strip())

    def _get_client(self):
        key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not key:
            raise AiKeyMissing(KEY_HELP)
        if self._client is None:
            from google import genai  # 키가 있을 때만 불러온다
            self._client = genai.Client(api_key=key)
        return self._client

    def generate_json(self, system: str, user_input: dict, retries: int | None = None) -> dict:
        """지시문 + 입력 -> JSON dict. 실패하면 1번 다시 시도 후 AiError (FR-02-3).
        retries=0 이면 다시 시도하지 않는다 (호출한 쪽이 검사까지 묶어 재시도할 때)."""
        client = self._get_client()
        user_text = json.dumps(user_input, ensure_ascii=False, indent=1)
        last_err: Exception | None = None
        n_retry = config.AI_RETRY if retries is None else retries
        for _attempt in range(1 + n_retry):
            self._wait_turn()
            self.calls += 1
            try:
                raw = _call_gemini(client, system, user_text)
                return parse_json_object(raw)
            except AiError as e:
                last_err = e
            except Exception as e:  # SDK 오류(네트워크·429·500 등)
                last_err = AiError(_safe_message(e))
        raise AiError(str(last_err))

    def _wait_turn(self) -> None:
        """분당 호출 한도를 넘지 않게 호출 사이를 띄운다."""
        gap = time.monotonic() - self._last_call
        if self._last_call and gap < config.AI_MIN_INTERVAL_SEC:
            time.sleep(config.AI_MIN_INTERVAL_SEC - gap)
        self._last_call = time.monotonic()


def _call_gemini(client, system: str, user_text: str) -> str:
    from google.genai import types
    resp = client.models.generate_content(
        model=config.AI_MODEL,
        contents=user_text,
        config=types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",   # JSON으로만 답하게 함
            temperature=config.AI_TEMPERATURE,
        ),
    )
    text = getattr(resp, "text", None)
    if not text:
        raise AiError("AI 응답이 비어 있음")
    return text


def parse_json_object(raw: str) -> dict:
    """AI 답을 JSON 객체로 읽는다. JSON이 아니거나 객체가 아니면 AiError (FR-02-3 예외)."""
    s = (raw or "").strip()
    # 일부 모델이 ```json ... ``` 으로 감싸는 경우만 벗긴다
    if s.startswith("```"):
        s = s.strip("`")
        if s.lower().startswith("json"):
            s = s[4:]
        s = s.strip()
    try:
        obj = json.loads(s)
    except (json.JSONDecodeError, TypeError) as e:
        raise AiError(f"JSON 아님: {e.msg if hasattr(e, 'msg') else e}") from None
    if not isinstance(obj, dict):
        raise AiError("JSON 객체({...})가 아님")
    return obj


def _safe_message(e: Exception) -> str:
    """오류 글에 키가 섞여 있으면 지운다 (NFR-06)."""
    msg = f"{type(e).__name__}: {e}"
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        msg = msg.replace(key, "***")
    return msg[:300]
