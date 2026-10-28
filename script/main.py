"""뉴스 봐 - 시험 실행 스크립트 (08 ADR-009 `main.py`, 가벼운 시험판).

실제 운영판과 다른 점 (시험용):
- Firestore 를 쓰지 않는다. 분야는 config.TRIAL_* 값, 결과는 sample_output/ 에 JSON·Markdown 으로 저장.
- 추천 뉴스(FR-01-6)는 하지 않는다. 관심 분야는 네이버 키가 있을 때만 1개 분야 시도.
- 원문 본문은 메모리에서만 쓰고 파일에 저장하지 않는다 (NFR-08). 저장하는 것은 글자 수뿐.

실행: .\\.venv\\Scripts\\python.exe main.py [--max-groups 1~3] [--no-naver] [--other-lines]
종료 코드: 0 = 끝까지 완료, 2 = Gemini 키가 없어 AI 단계 전에 멈춤(모으기·추출 결과는 저장됨), 1 = 오류.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime

import config
from ai_client import KEY_HELP, AiClient, AiError
from ai_tasks import Tasks
from collect import KST, Group, RawArticle, collect_naver, fetch_google_top, naver_keys
from extract import extract_text
from google_link import decode


# ---------------- 실행 기록 (D2 runs 모양 + 시험용 단계별 시간) ----------------
class Run:
    def __init__(self) -> None:
        self.started = datetime.now(KST)
        self.run_id = self.started.strftime("%Y%m%d-%H%M")
        h = self.started.hour
        self.slot = "morning" if h < 10 else ("noon" if h < 16 else "evening")  # 06 4-2
        self.timings: dict[str, float] = {}
        self.warnings: list[dict] = []
        self.page_results = {"today": {"result": "empty", "count": 0},
                             "interest": {"result": "empty", "count": 0},
                             "recommend": {"result": "empty", "count": 0}}
        self.decode = {"tried": 0, "succeeded": 0}
        self.extract = {"tried": 0, "succeeded": 0}
        self._t0 = time.monotonic()

    def warn(self, code: str, detail: str = "") -> None:
        self.warnings.append({"code": code, "detail": detail})
        print(f"  [경고] {code} {detail}".rstrip())

    def step(self, name: str):
        run = self

        class _Step:
            def __enter__(self_inner):
                self_inner.t = time.monotonic()
                print(f"\n== {name} ==")

            def __exit__(self_inner, *exc):
                sec = round(time.monotonic() - self_inner.t, 2)
                run.timings[name] = round(run.timings.get(name, 0) + sec, 2)
                print(f"   ({sec}초)")
                return False
        return _Step()

    def total_sec(self) -> float:
        return round(time.monotonic() - self._t0, 2)


def iso(dt: datetime | None) -> str | None:
    return dt.isoformat(timespec="seconds") if dt else None


# ---------------- 단계 함수 ----------------
def prepare_group(g: Group, run: Run) -> None:
    """구글 링크 해독(ADR-007) + 본문 추출(FR-02-2). 본문은 g.articles[].text (메모리)."""
    for a in g.articles:
        if a.link_type == "google":
            run.decode["tried"] += 1
            a.decode_tried = True
            url, ok = decode(a.url)
            if ok:
                run.decode["succeeded"] += 1
                a.url, a.link_type = url, "original"
        if a.link_type == "google":       # 해독 실패 -> 원문 주소가 없으니 추출 시도 안 함
            a.extract_result = "not_tried"
            continue
        run.extract["tried"] += 1
        text, result = extract_text(a.url)
        a.text, a.extract_result = text, result
        if result == "ok":
            run.extract["succeeded"] += 1
        print(f"   - {a.extract_result:<11} {len(a.text):>5}자  {(a.press or '')[:12]:<12} {a.title[:40]}")


def ai_inputs(g: Group) -> list[dict]:
    """T3 입력: 본문 > 요약 > 빈 값 순서 (FR-02-2 '실패하면 요약만')."""
    return [{"press": a.press or "", "title": a.title, "text": a.text or a.summary}
            for a in g.articles]


def build_article(run: Run, g: Group, order: int, res: dict) -> dict:
    """AI 결과 + 출처 -> D3 articles 한 칸 (06 3-4)."""
    return {
        "articleId": f"{run.run_id}_{g.page}_{order}",
        "page": g.page, "order": order,
        "hookLine": res["hookLine"], "title": res["title"], "body": res["body"],
        "conclusion": res["conclusion"], "isNotify": False,
        "createdAt": iso(datetime.now(KST)), "carriedFrom": None,
        "words": res["words"],
        "sources": [{"press": a.press or "", "title": a.title, "url": a.url,
                     "linkType": a.link_type, "publishedAt": iso(a.published_at),
                     "extractResult": a.extract_result} for a in g.articles],
    }


def describe_candidates(groups: list[Group], chosen: list[Group]) -> list[dict]:
    """sample_output 에 남길 수집 결과. 본문은 남기지 않고 글자 수만."""
    out = []
    for g in groups:
        out.append({
            "page": g.page, "topic": g.topic, "chosen": any(g is c for c in chosen),
            "sources": [{"press": a.press, "title": a.title, "url": a.url, "linkType": a.link_type,
                         "decodeTried": a.decode_tried, "extractResult": a.extract_result,
                         "extractedChars": len(a.text)} for a in g.articles],
        })
    return out


# ---------------- 저장 ----------------
def save(run: Run, status: str, edition: dict | None, candidates: list[dict],
         ai: AiClient, notes: list[str]) -> tuple[str, str]:
    config.OUTPUT_DIR.mkdir(exist_ok=True)
    finished = datetime.now(KST)
    record = {
        "runId": run.run_id, "slot": run.slot, "trigger": "manual",
        "startedAt": iso(run.started), "finishedAt": iso(finished),
        "durationSec": run.total_sec(), "status": status,
        "editionId": edition["editionId"] if edition else None,
        "categoriesUsed": {"first": config.TRIAL_FIRST, "deep": config.TRIAL_DEEP,
                           "second": config.TRIAL_SECOND} if naver_keys() else None,
        "pageResults": run.page_results,
        "otherLinesCount": len(edition["otherLines"]) if edition else 0,
        "aiCalls": ai.calls, "googleDecode": run.decode, "extract": run.extract,
        "warnings": run.warnings, "errorMessage": None, "schemaVersion": 1,
        # ---- 시험 실행에만 있는 칸 ----
        "stepTimingsSec": run.timings,
    }
    doc = {
        "trial": {
            "about": "시험 실행 결과. Firestore에 저장하지 않음. 원문 본문은 저장하지 않고 글자 수만 남김(NFR-08).",
            "model": config.AI_MODEL, "geminiKey": AiClient.has_key(),
            "naverKey": naver_keys() is not None, "notes": notes,
        },
        "run": record, "edition": edition, "collected": candidates,
    }
    base = config.OUTPUT_DIR / f"run_{run.run_id}"
    jpath, mpath = base.with_suffix(".json"), base.with_suffix(".md")
    jpath.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    mpath.write_text(to_markdown(doc), encoding="utf-8")
    return str(jpath), str(mpath)


def to_markdown(doc: dict) -> str:
    r, e, t = doc["run"], doc["edition"], doc["trial"]
    L = [f"# 뉴스 봐 시험 실행 결과 - {r['runId']}", "",
         "| 항목 | 값 |", "|---|---|",
         f"| 상태 | {r['status']} |", f"| 회차 | {r['slot']} |",
         f"| AI 모델 | {t['model']} (키 {'있음' if t['geminiKey'] else '없음'}) |",
         f"| 네이버 키 | {'있음' if t['naverKey'] else '없음'} |",
         f"| 전체 걸린 시간 | {r['durationSec']}초 |",
         f"| AI 호출 수 | {r['aiCalls']} |",
         f"| 구글 링크 해독 | {r['googleDecode']['succeeded']}/{r['googleDecode']['tried']} 성공 |",
         f"| 본문 추출 | {r['extract']['succeeded']}/{r['extract']['tried']} 성공 |", "",
         "## 단계별 걸린 시간", "", "| 단계 | 초 |", "|---|---:|"]
    L += [f"| {k} | {v} |" for k, v in r["stepTimingsSec"].items()]
    if t["notes"]:
        L += ["", "## 메모", ""] + [f"- {n}" for n in t["notes"]]
    if r["warnings"]:
        L += ["", "## 경고", ""] + [f"- `{w['code']}` {w['detail']}" for w in r["warnings"]]
    if e:
        L += ["", "## 종합 기사", ""]
        for a in e["articles"]:
            mark = " 🔔 알림용" if a["isNotify"] else ""
            L += [f"### [{a['page']} #{a['order']}] {a['hookLine']}{mark}", "",
                  "> \"오늘의 한 문장\"은 흥미를 위해 사실을 과장할 수 있어요. 정확한 내용은 꼭 기사 본문에서 확인해 주세요.", "",
                  f"**{a['title']}** ({len(a['body'])}자)", "", a["body"], "",
                  f"**한 줄 결론**: {a['conclusion']}", ""]
            if a["words"]:
                L += ["어려운 단어:"] + [f"- **{w['word']}**: {w['explanation']}" for w in a["words"]] + [""]
            L += ["출처:"] + [f"- {s['press']} · [{s['title']}]({s['url']}) ({s['linkType']}, 추출 {s['extractResult']})"
                             for s in a["sources"]] + [""]
        if e["otherLines"]:
            L += ["## 다른 분야 한 줄", ""] + [f"- [{o['category']}] [{o['hookLine']}]({o['url']})" for o in e["otherLines"]]
    L += ["", "## 모은 기사 묶음 (본문은 저장하지 않음, 글자 수만)", ""]
    for c in doc["collected"]:
        L += [f"### {'✅ 선택' if c['chosen'] else '후보'} [{c['page']}] {c['topic']}", "",
              "| 언론사 | 제목 | 링크 종류 | 추출 결과 | 추출 글자 수 |", "|---|---|---|---|---:|"]
        L += [f"| {s['press'] or ''} | {s['title'].replace('|', '/')} | {s['linkType']} | {s['extractResult']} | {s['extractedChars']} |"
              for s in c["sources"]]
        L.append("")
    return "\n".join(L) + "\n"


# ---------------- 전체 흐름 ----------------
def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # PowerShell 한글 깨짐 방지
    except AttributeError:
        pass
    ap = argparse.ArgumentParser(description="뉴스 봐 시험 실행")
    ap.add_argument("--max-groups", type=int, default=3, choices=[1, 2, 3],
                    help="오늘의 화제 묶음 최대 수 (기본 3)")
    ap.add_argument("--no-naver", action="store_true", help="네이버 키가 있어도 관심 분야를 건너뜀")
    ap.add_argument("--other-lines", action="store_true", help="다른 분야 한 줄(T4)도 시도 (네이버 키 필요)")
    args = ap.parse_args(argv)

    run, ai = Run(), AiClient()
    tasks = Tasks(ai)
    has_key = AiClient.has_key()
    use_naver = naver_keys() is not None and not args.no_naver
    notes: list[str] = []
    print(f"뉴스 봐 시험 실행 {run.run_id} / 모델 {config.AI_MODEL} / "
          f"Gemini 키 {'있음' if has_key else '없음'} / 네이버 키 {'있음' if naver_keys() else '없음'}")
    if not tasks.hook_examples:
        run.warn("EXAMPLES_FILE_MISSING")

    all_groups: list[Group] = []
    chosen: list[Group] = []
    backups: list[Group] = []      # 오늘의 화제: 고르지 않은 후보 (건너뛸 때 다음 순서로 사용)

    # ① 오늘의 화제 모으기 (A1, FR-01-4)
    today: list[Group] = []
    with run.step("1 오늘의 화제 RSS 모으기"):
        try:
            today = fetch_google_top()
            print(f"   후보 묶음 {len(today)}개, 기사 {sum(len(g.articles) for g in today)}개")
        except Exception as e:
            run.warn("PAGE_SKIPPED", f"today: RSS 오류 {type(e).__name__}")
    all_groups += today

    # ② 오늘의 화제 고르기 (T1)
    if today:
        with run.step("2 오늘의 화제 고르기(AI T1)"):
            order = list(range(len(today)))
            if has_key:
                try:
                    picked = tasks.pick_today([{"title": g.topic, "related": [a.title for a in g.articles[1:]]}
                                               for g in today])
                    order = picked + [i for i in range(len(today)) if i not in picked]
                    n = len(picked)
                except AiError as e:
                    run.warn("PICK_FALLBACK", f"today: {e}")
                    n = args.max_groups
            else:
                notes.append("Gemini 키 없음 -> 오늘의 화제는 AI 고르기 대신 RSS 위에서부터 사용 (PICK_FALLBACK 과 같은 동작)")
                n = args.max_groups
            n = min(n, args.max_groups)
            chosen += [today[i] for i in order[:n]]
            backups = [today[i] for i in order[n:]]
            print(f"   고른 묶음: {[g.topic[:25] for g in chosen]}")

    # ③ 나의 관심 분야 (A2 + T2, FR-01-5) - 네이버 키가 있을 때만
    if use_naver:
        with run.step("3 나의 관심 분야 네이버 검색 + 묶기(AI T2)"):
            try:
                kws = config.deep_keywords(config.TRIAL_DEEP)
                items, widened = collect_naver(kws)
                if widened:
                    run.warn("WINDOW_48H", "interest")
                items = items[:40]   # AI 에 보내는 양 제한 (시험용)
                print(f"   키워드 {kws} -> 기사 {len(items)}개")
                groups_idx: list[list[int]] = []
                topics: list[str] = []
                picked_g: list[int] | None = None
                if items and has_key:
                    try:
                        groups_idx, topics, picked_g = tasks.group_and_pick(
                            config.CATEGORIES[config.TRIAL_FIRST]["name"],
                            [{"title": a.title, "summary": a.summary} for a in items])
                    except AiError as e:
                        run.warn("GROUP_FALLBACK", f"interest: {e}")
                if not groups_idx:   # 키 없음 or 묶기 실패 -> 최신순 1개씩
                    groups_idx = [[i] for i in range(len(items))]
                    topics = [items[i].title for i in range(len(items))]
                if picked_g is None:
                    if has_key and items:
                        run.warn("PICK_FALLBACK", "interest")
                    picked_g = list(range(min(3, len(groups_idx))))
                ig = [Group(page="interest", topic=topics[p] or items[groups_idx[p][0]].title,
                            articles=[items[i] for i in groups_idx[p]]) for p in picked_g]
                chosen += ig
                all_groups += ig
            except Exception as e:
                run.warn("PAGE_SKIPPED", f"interest: {type(e).__name__} {str(e)[:80]}")
    else:
        notes.append("네이버 키 없음(또는 --no-naver) -> 나의 관심 분야 건너뜀")

    # ④ 링크 해독 + 본문 추출 (ADR-007, FR-02-2)
    with run.step("4 구글 링크 해독 + 본문 추출"):
        for g in chosen:
            print(f"  [{g.page}] {g.topic[:40]}")
            prepare_group(g, run)
    if run.decode["tried"] and run.decode["succeeded"] < run.decode["tried"]:
        run.warn("GOOGLE_DECODE_LOW", f"{run.decode['succeeded']}/{run.decode['tried']}")

    # ⑤ AI 단계 - 키가 없으면 여기서 친절하게 멈춘다
    if not has_key:
        print("\n" + KEY_HELP)
        run.warn("AI_KEY_MISSING", "시험 실행 전용 경고")
        for g in chosen:
            run.page_results[g.page]["result"] = "empty"
        j, m = save(run, "no_result", None, describe_candidates(all_groups, chosen), ai, notes)
        print(f"\n모으기·추출 결과만 저장했습니다:\n  {j}\n  {m}")
        return 2

    articles: list[dict] = []
    group_of: dict[str, Group] = {}
    with run.step("5 종합 기사 + 단어 해설 + 어그로 한 줄(AI T3)"):
        queue = list(chosen)
        counters = {"today": 0, "interest": 0, "recommend": 0}
        while queue:
            g = queue.pop(0)
            no_text = all(not a.text for a in g.articles) and all(not a.summary for a in g.articles)
            if no_text:
                if len(g.articles) <= 1:        # 제목 1개뿐 -> 건너뛰고 다음 순서 묶음 (FR-02-2)
                    run.warn("AI_GROUP_SKIPPED", f"{g.page}: 제목 1개뿐, 본문 없음")
                    if g.page == "today" and backups:
                        nxt = backups.pop(0)
                        print(f"  다음 순서 묶음으로 대체: {nxt.topic[:40]}")
                        prepare_group(nxt, run)
                        chosen.append(nxt)
                        queue.insert(0, nxt)
                    continue
                run.warn("TITLE_ONLY", f"{g.page}: {g.topic[:30]}")
            order = counters[g.page] + 1
            try:
                res, warns = tasks.write_article(ai_inputs(g))
            except AiError as e:
                run.warn("AI_GROUP_SKIPPED", f"{g.page} #{order}: {e}")
                continue
            for w in warns:
                run.warn("BODY_LENGTH", f"{g.page} #{order}: {w}")
            counters[g.page] = order
            art = build_article(run, g, order, res)
            articles.append(art)
            group_of[art["articleId"]] = g
            print(f"  [{g.page} #{order}] {res['hookLine']}  (본문 {len(res['body'])}자, 단어 {len(res['words'])}개)")
        for p, c in counters.items():
            if c:
                run.page_results[p] = {"result": "new", "count": c}

    # ⑥ 다른 분야 한 줄 (T4, FR-01-9) - 선택
    other_lines: list[dict] = []
    if args.other_lines and use_naver:
        with run.step("6 다른 분야 한 줄(AI T4)"):
            from collect import naver_search
            others = [c for c in config.CATEGORIES if c not in (config.TRIAL_FIRST, config.TRIAL_SECOND)]
            cands: dict[str, list[RawArticle]] = {}
            for cat in others:
                try:
                    found = [a for a in naver_search(config.first_keyword_of_category(cat),
                                                     config.NAVER_DISPLAY_OTHER)]
                    if found:
                        cands[cat] = found
                except Exception as e:
                    run.warn("PAGE_SKIPPED", f"other {cat}: {type(e).__name__}")
            try:
                lines = tasks.other_lines({c: [{"title": a.title, "summary": a.summary} for a in arts]
                                           for c, arts in cands.items()})
                for ln in lines:
                    a = cands[ln["category"]][ln["index"]]
                    other_lines.append({"category": ln["category"], "hookLine": ln["hookLine"],
                                        "articleTitle": a.title, "url": a.url, "linkType": a.link_type,
                                        "press": a.press, "publishedAt": iso(a.published_at)})
            except AiError as e:
                run.warn("OTHER_LINES_HIDDEN", str(e))

    # ⑦ 알림용 한 줄 고르기 (T5, FR-04-2)
    notify_id = None
    if articles:
        with run.step("7 알림용 한 줄 고르기(AI T5)"):
            try:
                idx = tasks.pick_notify([{"hookLine": a["hookLine"], "title": a["title"],
                                          "sourceCount": len(a["sources"])} for a in articles])
            except AiError as e:
                run.warn("NOTIFY_FALLBACK", str(e))
                idx = max(range(len(articles)), key=lambda i: len(articles[i]["sources"]))
            articles[idx]["isNotify"] = True
            notify_id = articles[idx]["articleId"]
            print(f"   알림용: {articles[idx]['hookLine']}")

    page_rank = {"today": 0, "interest": 1, "recommend": 2}
    articles.sort(key=lambda a: (page_rank[a["page"]], a["order"]))
    edition = None
    if articles:
        edition = {"editionId": run.run_id, "slot": run.slot, "createdAt": iso(datetime.now(KST)),
                   "notifyArticleId": notify_id, "articles": articles,
                   "otherLines": other_lines, "schemaVersion": 1}
    failed_any = any(w["code"] in ("AI_GROUP_SKIPPED", "PAGE_SKIPPED") for w in run.warnings)
    status = "no_result" if not articles else ("partial" if failed_any else "success")
    j, m = save(run, status, edition, describe_candidates(all_groups, chosen), ai, notes)
    print(f"\n완료 ({status}). AI 호출 {ai.calls}번, 전체 {run.total_sec()}초\n  {j}\n  {m}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
