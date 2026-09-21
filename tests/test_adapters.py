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


def test_qq_authorized_without_token():
    assert authorized({}) is True


def test_wechat_webhook():
    e = wx.parse_webhook({"sender": "wxid_a", "content": "在吗", "msgid": "5"})
    assert e and e.platform == "wechat" and e.text == "在吗"
    assert wx.parse_webhook({"sender": "x", "content": "  "}) is None


def test_wcf_msg_parse():
    e = wx.parse_wcf_msg({"type": 1, "content": "hi", "sender": "wxid_b", "id": "9"})
    assert e and e.user_id == "wxid_b"
    assert wx.parse_wcf_msg({"type": 0, "content": "hi", "sender": "wxid_b"}) is None
