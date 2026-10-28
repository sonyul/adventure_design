"""AI 작업 5가지와 결과 검사 (08 ADR-009 `ai_tasks.py`, 07 API명세서 3·4장).

T1 오늘의 화제 고르기 / T2 네이버 묶기·고르기 / T3 종합 기사+단어 해설+어그로 한 줄
T4 다른 분야 한 줄 / T5 알림용 한 줄 고르기.
검사 함수(validate_*)는 AI 없이도 시험할 수 있게 순수 함수로 둔다 (tests/test_ai_tasks.py).
"""
from __future__ import annotations

import re

import config
from ai_client import AiClient, AiError, AiKeyMissing

PROMPT_FILES = {
    "T1": "01_pick_today.txt",
    "T2": "02_group_pick.txt",
    "T3": "03_write_article.txt",
    "T4": "04_other_lines.txt",
    "T5": "05_pick_notify.txt",
}
HOOK_EXAMPLES_FILE = "hook_examples.txt"
NO_EXAMPLES_TEXT = "(예시 없음 - 위 규칙만 따른다)"


# ---------------- 지시문 읽기 (FR-03-1) ----------------
def load_hook_examples() -> list[str]:
    """예시 제목 파일 읽기. '#' 줄과 빈 줄은 뺀다. 파일이 없으면 빈 목록."""
    path = config.PROMPTS_DIR / HOOK_EXAMPLES_FILE
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    return [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]


def load_prompt(task: str, hook_examples: list[str] | None = None) -> str:
    text = (config.PROMPTS_DIR / PROMPT_FILES[task]).read_text(encoding="utf-8")
    if "{{HOOK_EXAMPLES}}" in text:
        ex = hook_examples if hook_examples is not None else load_hook_examples()
        filled = "\n".join(f"- {e}" for e in ex) if ex else NO_EXAMPLES_TEXT
        text = text.replace("{{HOOK_EXAMPLES}}", filled)
    return text


# ---------------- 공통 검사 도구 ----------------
def cut_hook(hook: str | None, fallback_title: str) -> str:
    """FR-03-2: 비면 제목으로 대신, 공백 포함 40자를 넘으면 앞 40자 + '…'."""
    h = " ".join((hook or "").split())
    if not h:
        h = " ".join((fallback_title or "").split())
    if len(h) > config.HOOK_MAX_CHARS:
        h = h[: config.HOOK_MAX_CHARS] + config.HOOK_ELLIPSIS
    return h


def _norm(s: str) -> str:
    """비교용: 공백을 모두 지운다 (줄바꿈·띄어쓰기 차이로 복사를 놓치지 않게)."""
    return re.sub(r"\s+", "", s or "")


def longest_copied_run(body: str, sources: list[str], limit: int = config.COPY_MAX_RUN) -> bool:
    """본문(body)에 원문과 똑같은 글자가 limit자 이상 이어지는 곳이 있으면 True.
    공백은 무시하고 비교한다 (FR-02-3 완료 기준 '50자 이상 원문 복사 금지')."""
    b = _norm(body)
    if len(b) < limit:
        return False
    windows: set[str] = set()
    for src in sources:
        s = _norm(src)
        for i in range(0, len(s) - limit + 1):
            windows.add(s[i:i + limit])
    if not windows:
        return False
    return any(b[i:i + limit] in windows for i in range(0, len(b) - limit + 1))


def _int_list(v) -> list[int]:
    if not isinstance(v, list):
        return []
    out = []
    for x in v:
        if isinstance(x, bool):
            continue
        if isinstance(x, int):
            out.append(x)
        elif isinstance(x, str) and x.strip().isdigit():
            out.append(int(x.strip()))
    return out


# ---------------- T1 오늘의 화제 고르기 ----------------
def validate_pick(resp: dict, n_candidates: int, max_pick: int = config.MAX_GROUPS_PER_PAGE) -> list[int]:
    """{"picked":[번호...]} -> 0부터 센 위치 목록. 하나도 못 고르면 AiError (-> 위에서 3개, PICK_FALLBACK)."""
    seen, out = set(), []
    for no in _int_list(resp.get("picked")):
        if 1 <= no <= n_candidates and no not in seen:
            seen.add(no)
            out.append(no - 1)
    if not out:
        raise AiError("picked 가 비었거나 범위 밖")
    return out[:max_pick]


# ---------------- T2 네이버 묶기·고르기 ----------------
def validate_groups(resp: dict, n_items: int) -> tuple[list[list[int]], list[str], list[int] | None]:
    """{"groups":[{"topic","items"}], "picked":[...]}
    -> (묶음별 기사 위치 목록, 묶음 주제, 고른 묶음 위치 목록 또는 None(고르기 실패)).
    묶기 자체가 틀리면 AiError (-> 최신순 1개씩 묶음, GROUP_FALLBACK)."""
    raw_groups = resp.get("groups")
    if not isinstance(raw_groups, list):
        raise AiError("groups 가 목록이 아님")
    used: set[int] = set()
    groups: list[list[int]] = []
    topics: list[str] = []
    index_map: dict[int, int] = {}   # AI 묶음 순번(1~) -> 정리 후 위치(0~)
    for gi, g in enumerate(raw_groups, start=1):
        if not isinstance(g, dict):
            continue
        items = []
        for no in _int_list(g.get("items")):
            if 1 <= no <= n_items and no not in used:
                used.add(no)
                items.append(no - 1)
        items = items[: config.MAX_ARTICLES_PER_GROUP]
        if items:
            index_map[gi] = len(groups)
            groups.append(items)
            topics.append(str(g.get("topic") or "").strip())
    if not groups:
        raise AiError("쓸 수 있는 묶음이 없음")
    picked: list[int] = []
    for no in _int_list(resp.get("picked")):
        pos = index_map.get(no)
        if pos is not None and pos not in picked:
            picked.append(pos)
    return groups, topics, (picked[: config.MAX_GROUPS_PER_PAGE] or None)


# ---------------- T3 종합 기사 + 단어 해설 + 어그로 한 줄 ----------------
def validate_article(resp: dict, source_texts: list[str]) -> tuple[dict, list[str]]:
    """T3 결과 검사. 돌려주는 값: (D3 필드로 옮길 dict, 경고 목록).
    실패(AiError): title/body/conclusion 이 비어 있음, 본문이 너무 짧음(300자 미만), 원문 50자 이상 복사."""
    title = " ".join(str(resp.get("title") or "").split())
    body = str(resp.get("body") or "").strip()
    conclusion = " ".join(str(resp.get("conclusion") or "").split())
    if not title or not body or not conclusion:
        raise AiError("title/body/conclusion 중 빈 값이 있음")
    if len(body) < config.BODY_HARD_MIN_CHARS:
        raise AiError(f"본문이 너무 짧음 ({len(body)}자)")
    if longest_copied_run(body, source_texts):
        raise AiError(f"원문과 {config.COPY_MAX_RUN}자 이상 같은 부분이 있음")
    warnings: list[str] = []
    if not (config.BODY_MIN_CHARS <= len(body) <= config.BODY_MAX_CHARS):
        warnings.append(f"BODY_LENGTH {len(body)}자")

    words: list[dict] = []
    seen: set[str] = set()
    raw_words = resp.get("words") if isinstance(resp.get("words"), list) else []
    for w in raw_words:
        if not isinstance(w, dict):
            continue
        word = str(w.get("word") or "").strip()
        expl = " ".join(str(w.get("explanation") or "").split())
        if not word or not expl or word in seen:
            continue
        if word not in body:          # 본문에 없는 단어는 버린다 (FR-02-4)
            continue
        seen.add(word)
        words.append({"word": word, "explanation": expl})
    words.sort(key=lambda x: body.find(x["word"]))   # 본문에 처음 나오는 순서 (06 3-5)
    words = words[: config.WORDS_MAX]

    hook = cut_hook(resp.get("hookLine"), title)
    return ({"title": title, "body": body, "conclusion": conclusion,
             "words": words, "hookLine": hook}, warnings)


# ---------------- T4 다른 분야 한 줄 ----------------
def validate_other_lines(resp: dict, candidates: dict[str, list[dict]]) -> list[dict]:
    """{"lines":[{"category","no","hookLine"}]} -> [{"category","index","hookLine"}].
    candidates: 분야 코드 -> 기사 목록(각 기사 dict 에 'title'). lines 가 목록이 아니면 AiError (-> 칸 숨김)."""
    raw = resp.get("lines")
    if not isinstance(raw, list):
        raise AiError("lines 가 목록이 아님")
    out: list[dict] = []
    done: set[str] = set()
    for ln in raw:
        if not isinstance(ln, dict):
            continue
        cat = str(ln.get("category") or "").strip()
        nos = _int_list([ln.get("no")])
        if cat not in candidates or cat in done or not nos:
            continue
        idx = nos[0] - 1
        if not (0 <= idx < len(candidates[cat])):
            continue
        done.add(cat)
        out.append({"category": cat, "index": idx,
                    "hookLine": cut_hook(ln.get("hookLine"), candidates[cat][idx]["title"])})
    order = list(config.CATEGORIES.keys())        # 저장 순서 = 큰 분야 코드표 순서 (06 3-7)
    out.sort(key=lambda x: order.index(x["category"]) if x["category"] in order else 99)
    return out


# ---------------- T5 알림용 한 줄 고르기 ----------------
def validate_notify(resp: dict, n: int) -> int:
    """{"picked": 번호} -> 0부터 센 위치. 틀리면 AiError (-> 원문 기사 수 최다, NOTIFY_FALLBACK)."""
    nos = _int_list([resp.get("picked")])
    if not nos or not (1 <= nos[0] <= n):
        raise AiError("picked 가 범위 밖")
    return nos[0] - 1


# ---------------- 실제 호출 (ai_client 경유) ----------------
class Tasks:
    def __init__(self, client: AiClient) -> None:
        self.client = client
        self.hook_examples = load_hook_examples()

    def pick_today(self, candidates: list[dict]) -> list[int]:
        """candidates: [{"title", "related":[...]}]"""
        inp = {"candidates": [{"no": i + 1, **c} for i, c in enumerate(candidates)]}
        resp = self.client.generate_json(load_prompt("T1"), inp)
        return validate_pick(resp, len(candidates))

    def group_and_pick(self, field_name: str, items: list[dict]):
        """items: [{"title","summary"}]"""
        inp = {"field": field_name,
               "articles": [{"no": i + 1, **it} for i, it in enumerate(items)]}
        resp = self.client.generate_json(load_prompt("T2"), inp)
        return validate_groups(resp, len(items))

    def write_article(self, articles: list[dict]) -> tuple[dict, list[str]]:
        """articles: [{"press","title","text"}] (text = 본문 3,000자 이하 또는 요약 또는 빈 값)"""
        inp = {"articles": articles}
        system = load_prompt("T3", self.hook_examples)
        sources = [a.get("text", "") for a in articles]
        last: AiError | None = None
        # 호출 오류·JSON 아님·형식 검사 실패(복사·빈 값)를 모두 '실패'로 보고,
        # 합쳐서 1번만 다시 시도한다 (FR-02-3 예외). -> 묶음당 최대 2번 호출
        for _ in range(1 + config.AI_RETRY):
            try:
                resp = self.client.generate_json(system, inp, retries=0)
                return validate_article(resp, sources)
            except AiKeyMissing:
                raise
            except AiError as e:
                last = e
        raise AiError(str(last))

    def other_lines(self, candidates: dict[str, list[dict]]) -> list[dict]:
        inp = {"categories": [
            {"category": cat, "name": config.CATEGORIES[cat]["name"],
             "articles": [{"no": i + 1, "title": a["title"], "summary": a.get("summary", "")}
                          for i, a in enumerate(arts)]}
            for cat, arts in candidates.items()]}
        resp = self.client.generate_json(load_prompt("T4", self.hook_examples), inp)
        return validate_other_lines(resp, candidates)

    def pick_notify(self, items: list[dict]) -> int:
        """items: [{"hookLine","title","sourceCount"}]"""
        inp = {"articles": [{"no": i + 1, **it} for i, it in enumerate(items)]}
        resp = self.client.generate_json(load_prompt("T5"), inp)
        return validate_notify(resp, len(items))
