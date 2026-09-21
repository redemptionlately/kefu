from askbot.core.knowledge import KnowledgeBase


def test_longest_match_wins():
    kb = KnowledgeBase({"货": "A1", "退货": "A7"})
    assert kb.search("退货政策是什么") == "A7"


def test_no_match():
    assert KnowledgeBase({"运费": "x"}).search("你是谁") is None


def test_from_json_missing():
    assert KnowledgeBase.from_json("data/not-exist.json").faq == {}


def test_from_json_list_format(tmp_path):
    p = tmp_path / "faq.json"
    p.write_text('[{"q": "发票", "a": "电子发票"}]', encoding="utf-8")
    assert KnowledgeBase.from_json(p).search("怎么开发票") == "电子发票"
