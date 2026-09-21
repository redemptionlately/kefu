from askbot.adapters.qq import QQAdapter, authorized
from askbot.adapters.wechat import WeChatAdapter

qq = QQAdapter()
wx = WeChatAdapter(mode="log")


def test_qq_private():
    e = qq.parse_webhook(
        {"post_type": "message", "message_type": "private",
         "user_id": 123, "message_id": 1, "message": "你好"}
    )
    assert e and e.user_id == "123" and e.group_id is None


def test_qq_group_segmented():
    e = qq.parse_webhook(
        {"post_type": "message", "message_type": "group", "group_id": 99,
         "user_id": 7, "message_id": 2,
         "message": [{"type": "text", "data": {"text": "hi"}}]}
    )
    assert e and e.group_id == "99" and e.text == "hi"


def test_qq_non_message_ignored():
    assert qq.parse_webhook({"post_type": "notice"}) is None


def test_qq_image_segment_extracted():
    e = qq.parse_webhook(
        {"post_type": "message", "message_type": "private",
         "user_id": 5, "message_id": 3,
         "message": [
             {"type": "text", "data": {"text": "这是什么"}},
             {"type": "image", "data": {"url": "http://example.com/a.jpg"}},
             {"type": "image", "data": {"file": "local-only"}},
         ]}
    )
    assert e and e.text == "这是什么" and e.images == ["http://example.com/a.jpg"]


def test_qq_authorized_without_token():
    assert authorized({}) is True


def test_wechat_webhook():
    e = wx.parse_webhook({"sender": "wxid_a", "content": "在吗", "msgid": "5"})
    assert e and e.platform == "wechat" and e.text == "在吗"
    assert wx.parse_webhook({"sender": "x", "content": "  "}) is None


def test_wechat_always_log_mode():
    assert WeChatAdapter(mode="ferry").mode == "log"
    assert WeChatAdapter().available() is False
