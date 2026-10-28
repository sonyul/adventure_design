"""AI 결과 검사 함수 단위 시험 - 가짜 AI 응답으로 확인한다 (Gemini 키 불필요).

실행 (script 폴더에서): .\\.venv\\Scripts\\python.exe -m unittest discover -s tests -v
"""
import json
import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
from ai_client import AiClient, AiError, AiKeyMissing, parse_json_object  # noqa: E402
from ai_tasks import (Tasks, cut_hook, load_hook_examples, load_prompt,  # noqa: E402
                      longest_copied_run, validate_article, validate_groups, validate_notify,
                      validate_other_lines, validate_pick, PROMPT_FILES)

BODY_OK = ("서울 지하철 노동조합이 내일부터 파업을 하겠다고 밝혔어요. " * 20)[:700]


class FakeClient:
    """미리 정한 답을 차례로 돌려주는 가짜 AI."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.calls = 0

    def generate_json(self, system, user_input, retries=None):
        self.calls += 1
        a = self.answers.pop(0)
        if isinstance(a, Exception):
            raise a
        return parse_json_object(a if isinstance(a, str) else json.dumps(a, ensure_ascii=False))


class TestJsonParse(unittest.TestCase):
    def test_not_json_is_failure(self):
        with self.assertRaises(AiError):
            parse_json_object("죄송하지만 JSON으로 답할 수 없어요")

    def test_array_is_failure(self):
        with self.assertRaises(AiError):
            parse_json_object("[1, 2]")

    def test_code_fence_is_unwrapped(self):
        self.assertEqual(parse_json_object('```json\n{"picked": [1]}\n```'), {"picked": [1]})


class TestHook(unittest.TestCase):
    def test_cut_40(self):
        h = cut_hook("가" * 45, "제목")
        self.assertEqual(h, "가" * 40 + "…")

    def test_exactly_40_not_cut(self):
        self.assertEqual(cut_hook("나" * 40, "제목"), "나" * 40)

    def test_empty_uses_title(self):
        self.assertEqual(cut_hook("   ", "종합 기사 제목"), "종합 기사 제목")

    def test_spaces_collapsed(self):
        self.assertEqual(cut_hook("내일  지하철\n멈춘다", "t"), "내일 지하철 멈춘다")


class TestCopyCheck(unittest.TestCase):
    SRC = "가나다라마바사아자차카타파하" * 10   # 140자

    def test_50_copy_detected(self):
        body = "새로 쓴 문장입니다. " + self.SRC[10:60] + " 끝."
        self.assertTrue(longest_copied_run(body, [self.SRC]))

    def test_49_copy_allowed(self):
        body = "새로 쓴 문장입니다. " + self.SRC[10:59] + " 끝."
        self.assertFalse(longest_copied_run(body, [self.SRC]))

    def test_whitespace_ignored(self):
        piece = self.SRC[0:60]
        spaced = " ".join(piece[i:i + 5] for i in range(0, 60, 5))
        self.assertTrue(longest_copied_run(spaced, [self.SRC]))

    def test_empty_sources(self):
        self.assertFalse(longest_copied_run(BODY_OK, ["", "짧음"]))


class TestValidateArticle(unittest.TestCase):
    def good(self, **kw):
        r = {"title": "지하철 노조 내일 파업 예고", "body": BODY_OK,
             "conclusion": "출근길을 미리 확인해요.",
             "words": [{"word": "파업", "explanation": "일을 함께 멈추는 거예요."},
                       {"word": "노동조합", "explanation": "일하는 사람들의 모임이에요."},
                       {"word": "없는단어", "explanation": "본문에 없음"},
                       {"word": "파업", "explanation": "중복"}],
             "hookLine": "내일 아침, 지하철이 멈춘다고? 출근길 비상 걸린 이유 총정리 지금 바로 확인하세요"}
        r.update(kw)
        return r

    def test_ok_and_rules(self):
        out, warns = validate_article(self.good(), ["전혀 다른 원문 내용입니다."])
        self.assertEqual(warns, [])
        self.assertEqual([w["word"] for w in out["words"]], ["노동조합", "파업"])  # 본문 첫 등장 순서
        self.assertLessEqual(len(out["hookLine"]), 41)
        self.assertTrue(out["hookLine"].endswith("…"))

    def test_words_max_5(self):
        words = [{"word": w, "explanation": "설명"} for w in ["서울", "지하철", "노동조합", "내일", "파업", "밝혔어요"]]
        out, _ = validate_article(self.good(words=words), [])
        self.assertEqual(len(out["words"]), 5)

    def test_missing_field_fails(self):
        with self.assertRaises(AiError):
            validate_article(self.good(conclusion=""), [])

    def test_too_short_fails(self):
        with self.assertRaises(AiError):
            validate_article(self.good(body="짧은 글" * 10), [])

    def test_length_warning(self):
        _, warns = validate_article(self.good(body=BODY_OK[:450]), [])
        self.assertEqual(len(warns), 1)
        self.assertIn("BODY_LENGTH", warns[0])

    def test_copy_fails(self):
        with self.assertRaises(AiError):
            validate_article(self.good(), [BODY_OK[100:200]])

    def test_empty_hook_uses_title(self):
        out, _ = validate_article(self.good(hookLine=""), [])
        self.assertEqual(out["hookLine"], "지하철 노조 내일 파업 예고")

    def test_words_not_list_ok(self):
        out, _ = validate_article(self.good(words="없음"), [])
        self.assertEqual(out["words"], [])


class TestValidatePickGroupsNotify(unittest.TestCase):
    def test_pick(self):
        self.assertEqual(validate_pick({"picked": [3, "1", 3, 9, 2, 4]}, 5), [2, 0, 1])

    def test_pick_empty_fails(self):
        with self.assertRaises(AiError):
            validate_pick({"picked": []}, 5)
        with self.assertRaises(AiError):
            validate_pick({"picked": [0, 6]}, 5)

    def test_groups(self):
        resp = {"groups": [{"topic": "A", "items": [1, 2, 3, 4, 5, 6, 7]},
                           {"topic": "빈", "items": [99]},
                           {"topic": "B", "items": [2, 8]}],
                "picked": [3, 1, 2]}
        groups, topics, picked = validate_groups(resp, 10)
        self.assertEqual(groups, [[0, 1, 2, 3, 4], [7]])   # 5개 제한, 중복(2) 제거, 빈 묶음 제거
        self.assertEqual(topics, ["A", "B"])
        self.assertEqual(picked, [1, 0])                    # 순번 3 -> 위치 1, 순번 2(빈 묶음)는 버림

    def test_groups_pick_missing(self):
        _, _, picked = validate_groups({"groups": [{"items": [1]}]}, 3)
        self.assertIsNone(picked)

    def test_groups_invalid(self):
        with self.assertRaises(AiError):
            validate_groups({"groups": "x"}, 3)

    def test_notify(self):
        self.assertEqual(validate_notify({"picked": 2}, 3), 1)
        with self.assertRaises(AiError):
            validate_notify({"picked": 4}, 3)
        with self.assertRaises(AiError):
            validate_notify({"picked": True}, 3)

    def test_other_lines(self):
        cands = {"sports": [{"title": "야구 끝내기"}], "life": [{"title": "a"}, {"title": "b"}]}
        resp = {"lines": [{"category": "sports", "no": 1, "hookLine": ""},
                          {"category": "life", "no": 2, "hookLine": "오늘 밤 " + "길게" * 30},
                          {"category": "life", "no": 1, "hookLine": "중복 분야"},
                          {"category": "politics", "no": 1, "hookLine": "입력에 없는 분야"}]}
        out = validate_other_lines(resp, cands)
        self.assertEqual([o["category"] for o in out], ["sports", "life"])   # 큰 분야 코드표 순서
        self.assertEqual(out[0]["hookLine"], "야구 끝내기")
        self.assertTrue(out[1]["hookLine"].endswith("…"))


class TestTasksRetry(unittest.TestCase):
    def test_write_article_retry_once_then_success(self):
        fake = FakeClient(["JSON 아님", {"title": "t", "body": BODY_OK, "conclusion": "c",
                                         "words": [], "hookLine": "h"}])
        t = Tasks(fake)
        out, _ = t.write_article([{"press": "p", "title": "t", "text": ""}])
        self.assertEqual(fake.calls, 2)
        self.assertEqual(out["hookLine"], "h")

    def test_write_article_two_failures_skip(self):
        fake = FakeClient([AiError("429"), {"title": "", "body": "", "conclusion": ""}])
        with self.assertRaises(AiError):
            Tasks(fake).write_article([{"press": "p", "title": "t", "text": ""}])
        self.assertEqual(fake.calls, 2)


class TestPromptsAndKey(unittest.TestCase):
    def test_examples_draft_15(self):
        ex = load_hook_examples()
        self.assertEqual(len(ex), 15)

    def test_placeholder_filled(self):
        for task in PROMPT_FILES:
            p = load_prompt(task)
            self.assertNotIn("{{", p)
        self.assertIn("- 내일부터 지갑이 얇아진다?", load_prompt("T3"))

    def test_no_key_message(self):
        import os
        saved = os.environ.pop("GEMINI_API_KEY", None)
        try:
            self.assertFalse(AiClient.has_key())
            with self.assertRaises(AiKeyMissing) as cm:
                AiClient().generate_json("s", {})
            self.assertIn("aistudio.google.com/apikey", str(cm.exception))
        finally:
            if saved is not None:
                os.environ["GEMINI_API_KEY"] = saved


class TestDocMatchesPromptFiles(unittest.TestCase):
    """07_API명세서.md 에 실린 지시문 전문이 prompts/ 파일과 글자 하나까지 같은지 확인."""

    def test_doc_blocks_equal_files(self):
        doc = (config.BASE_DIR.parent / "docs" / "design" / "07_API명세서.md").read_text(encoding="utf-8")
        names = list(PROMPT_FILES.values()) + ["hook_examples.txt"]
        for name in names:
            m = re.search(r"<!-- prompt-file: " + re.escape(name) + r" -->\n```text\n(.*?)```\n", doc, re.S)
            self.assertIsNotNone(m, f"문서에 {name} 전문 블록이 없음")
            file_text = (config.PROMPTS_DIR / name).read_text(encoding="utf-8")
            self.assertEqual(m.group(1), file_text, f"{name} 내용이 문서와 다름")


if __name__ == "__main__":
    unittest.main()
