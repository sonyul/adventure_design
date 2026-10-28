"""모으기 도구 + 전체 흐름 시험 (인터넷·키 없이, 가짜 부품으로).

실행 (script 폴더에서): .\\.venv\\Scripts\\python.exe -m unittest discover -s tests -v
"""
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
import main  # noqa: E402
from collect import (KST, Group, RawArticle, _filter_window, _ListParser,  # noqa: E402
                     clean_naver_text, press_from_url)

MARK = "ZZ원문표식ZZ "   # 가짜 원문 본문 - 결과 파일에 나오면 안 됨
BODY = ("새로 정리한 종합 기사 문장이에요. 쉬운 말로 다시 썼어요. " * 30)[:720]


class TestCollectHelpers(unittest.TestCase):
    def test_rss_description_list(self):
        p = _ListParser()
        p.feed('<ol><li><a href="https://news.google.com/rss/articles/A" target="_blank">제목 하나</a>'
               '&nbsp;&nbsp;<font color="#6f6f6f">한빛일보</font></li>'
               '<li><a href="https://news.google.com/rss/articles/B">제목 둘</a> <font>누리신문</font></li></ol>')
        self.assertEqual([i["press"] for i in p.items], ["한빛일보", "누리신문"])
        self.assertEqual(p.items[1]["url"], "https://news.google.com/rss/articles/B")

    def test_clean_naver(self):
        self.assertEqual(clean_naver_text("<b>우주</b> 발사 &quot;성공&quot;"), '우주 발사 "성공"')

    def test_press_from_url(self):
        self.assertEqual(press_from_url("https://www.hanbit.co.kr/news/1"), "hanbit.co.kr")
        self.assertEqual(press_from_url("https://m.example.com/a"), "example.com")

    def test_window_and_dedupe(self):
        now = datetime(2026, 10, 28, 12, 0, tzinfo=KST)
        a = RawArticle("a", "u1", "original", published_at=now - timedelta(hours=1))
        b = RawArticle("b", "u1", "original", published_at=now - timedelta(hours=2))   # 같은 링크
        c = RawArticle("c", "u2", "original", published_at=now - timedelta(hours=30))  # 24시간 밖
        out = _filter_window([b, a, c], now, 24)
        self.assertEqual([x.title for x in out], ["a"])
        self.assertEqual(len(_filter_window([a, c], now, 48)), 2)


def fake_ai(self, system, user_input, retries=None):
    """지시문 내용으로 어떤 작업인지 알아보고 정해진 답을 준다."""
    self.calls += 1
    if "주요 뉴스" in system:                       # T1
        return {"picked": [2, 1], "reason": "시험"}
    if "기자다" in system:                         # T3
        title = user_input["articles"][0]["title"]
        return {"title": f"정리: {title}", "body": BODY, "conclusion": "기억해 두세요.",
                "words": [{"word": "종합", "explanation": "여럿을 하나로 모은 것."}],
                "hookLine": "지금 안 보면 후회할 소식이 왔다 " * 3}
    if "알림으로 딱" in system:                     # T5
        return {"picked": 2}
    raise AssertionError("예상하지 못한 작업")


def fake_groups(limit=5):
    gs = []
    for i in range(1, 4):
        arts = [RawArticle(f"사건{i} 기사{j}", f"https://news.google.com/rss/articles/{i}{j}", "google",
                           press=f"언론{j}") for j in range(1, 3)]
        gs.append(Group(page="today", topic=f"사건{i}", articles=arts))
    return gs


class TestMainFlow(unittest.TestCase):
    def run_main(self, has_key):
        tmp = tempfile.mkdtemp()
        with mock.patch.object(config, "OUTPUT_DIR", Path(tmp)), \
             mock.patch.object(main, "fetch_google_top", fake_groups), \
             mock.patch.object(main, "decode", lambda u: (u.replace("news.google.com/rss/articles", "press.example"), True)), \
             mock.patch.object(main, "extract_text", lambda u: (MARK * 40, "ok")), \
             mock.patch.object(main, "naver_keys", lambda: None), \
             mock.patch.object(main.AiClient, "has_key", staticmethod(lambda: has_key)), \
             mock.patch.object(main.AiClient, "generate_json", fake_ai), \
             mock.patch("builtins.print"):
            code = main.main([])
        files = sorted(Path(tmp).glob("run_*.json"))
        return code, json.loads(files[-1].read_text(encoding="utf-8")), sorted(Path(tmp).glob("run_*.md"))

    def test_with_fake_ai(self):
        code, doc, mds = self.run_main(True)
        self.assertEqual(code, 0)
        self.assertEqual(len(mds), 1)
        ed, run = doc["edition"], doc["run"]
        self.assertEqual(run["status"], "success")
        self.assertEqual(run["aiCalls"], 4)                      # T1 1 + T3 2 + T5 1
        self.assertEqual([a["order"] for a in ed["articles"]], [1, 2])
        self.assertEqual(ed["articles"][0]["sources"][0]["linkType"], "original")
        self.assertTrue(ed["articles"][0]["hookLine"].endswith("…"))
        self.assertEqual(ed["notifyArticleId"], ed["articles"][1]["articleId"])
        self.assertEqual(sum(a["isNotify"] for a in ed["articles"]), 1)
        self.assertEqual(run["pageResults"]["today"], {"result": "new", "count": 2})
        # 원문 본문이 결과 파일에 들어가지 않았는지 (NFR-08)
        self.assertNotIn(MARK.strip(), json.dumps(doc, ensure_ascii=False))

    def test_without_key_stops_kindly(self):
        code, doc, _ = self.run_main(False)
        self.assertEqual(code, 2)
        self.assertIsNone(doc["edition"])
        self.assertEqual(doc["run"]["aiCalls"], 0)
        self.assertEqual(doc["run"]["extract"], {"tried": 6, "succeeded": 6})
        self.assertIn("AI_KEY_MISSING", [w["code"] for w in doc["run"]["warnings"]])
        self.assertNotIn(MARK.strip(), json.dumps(doc, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
