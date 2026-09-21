"""OneBot webhook 端到端:TestClient 打 /webhook/onebot,走真实引擎."""
from fastapi.testclient import TestClient

from askbot.app import app


def _private(text: str, user_id: int = 123) -> dict:
    return {
        "post_type": "message",
        "message_type": "private",
        "user_id": user_id,
        "message_id": 1,
        "message": text,
    }


def test_healthz():
    with TestClient(app) as c:
        r = c.get("/healthz")
        assert r.status_code == 200
        assert r.json()["ok"] is True


def test_onebot_private_ok():
    with TestClient(app) as c:
        r = c.post("/webhook/onebot", json=_private("你好"))
        assert r.status_code == 200
        assert r.json() == {"ok": True}


def test_onebot_non_message_ignored():
    with TestClient(app) as c:
        r = c.post("/webhook/onebot", json={"post_type": "notice"})
        assert r.json() == {"ignored": True}


def test_onebot_unauthorized():
    from askbot.config import settings

    old = settings.onebot_access_token
    settings.onebot_access_token = "secret"
    try:
        with TestClient(app) as c:
            r = c.post("/webhook/onebot", json=_private("hi"))
            assert r.status_code == 401
            r = c.post(
                "/webhook/onebot",
                json=_private("hi"),
                headers={"Authorization": "Bearer secret"},
            )
            assert r.status_code == 200
    finally:
        settings.onebot_access_token = old
