"""Tests for the unified WebSocket gateway at /service/ws.

These tests override the AI dependency to avoid real network calls.
"""
import json
import sys
import warnings
from pathlib import Path
from typing import AsyncIterator

import pytest
from starlette.testclient import TestClient


# 全局关闭告警，确保直接运行脚本时输出干净（仅用于本测试脚本）
warnings.filterwarnings("ignore")

# Ensure project root is importable when running `pytest` from repo root
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.main import app  # noqa: E402
from app.services.ai import get_ai_service  # noqa: E402
from app.services.ai.providers.base import AIChatResponse  # noqa: E402

TEST_TOKEN = "dev-token"


# 额外降噪（冗余兜底）——运行时仍旧忽略已知第三方库告警
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)


class _FakeAIService:
    """Minimal fake AI service used by tests.

    - chat: returns a fixed response
    - stream_chat: yields two small chunks then completes
    """

    async def chat(self, **kwargs) -> AIChatResponse:
        return AIChatResponse(
            text="hello from fake",
            model="fake-model-1",
            usage={"prompt_tokens": 3, "completion_tokens": 3, "total_tokens": 6},
        )

    async def stream_chat(self, **kwargs) -> AsyncIterator[str]:
        # Two deterministic chunks; FastAPI WS will flush each as a frame
        for chunk in ("hello ", "from fake"):
            yield chunk


@pytest.fixture()
def client():
    """Provide a TestClient with AI dependency overridden."""
    async def _override():
        return _FakeAIService()

    app.dependency_overrides[get_ai_service] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_ai_service, None)


def _send(ws, payload: dict) -> None:
    ws.send_text(json.dumps(payload))


def _recv(ws) -> dict:
    return json.loads(ws.receive_text())


def test_ws_ping(client: TestClient):
    with client.websocket_connect(f"/service/ws?token={TEST_TOKEN}") as ws:
        _send(ws, {"reqId": "r1", "op": "ping"})
        msg = _recv(ws)
        assert msg["reqId"] == "r1"
        assert msg["op"] == "ping"
        assert msg["event"] == "pong"


def test_ws_ai_chat(client: TestClient):
    with client.websocket_connect(f"/service/ws?token={TEST_TOKEN}") as ws:
        _send(
            ws,
            {
                "reqId": "r2",
                "op": "ai.chat",
                "data": {
                    "modelAlias": "default",
                    "messages": [{"role": "user", "content": "hi"}],
                },
            },
        )
        msg = _recv(ws)
        assert msg["reqId"] == "r2"
        assert msg["op"] == "ai.chat"
        assert msg["event"] == "result"
        assert msg["text"] == "hello from fake"
        assert msg["model"] == "fake-model-1"
        assert isinstance(msg.get("usage"), dict)


def test_ws_ai_stream(client: TestClient):
    with client.websocket_connect(f"/service/ws?token={TEST_TOKEN}") as ws:
        _send(
            ws,
            {
                "reqId": "r3",
                "op": "ai.stream",
                "data": {
                    "modelAlias": "default",
                    "messages": [{"role": "user", "content": "stream please"}],
                },
            },
        )

        # Expect start -> chunk -> chunk -> final -> done
        start = _recv(ws)
        assert start["event"] == "start"
        assert start["reqId"] == "r3"
        c1 = _recv(ws)
        c2 = _recv(ws)
        assert c1["event"] == "chunk" and c1["text"] == "hello "
        assert c2["event"] == "chunk" and c2["text"] == "from fake"
        final = _recv(ws)
        assert final["event"] == "final"
        assert final["text"] == "hello from fake"
        done = _recv(ws)
        assert done["event"] == "done"
        # model/usage may be null for now
        assert done.get("reqId") == "r3"


def test_ws_room_typing_broadcast(client: TestClient):
    # Two clients join the same room; one sends typing and the other gets an update
    with client.websocket_connect(f"/service/ws?token={TEST_TOKEN}") as ws1, client.websocket_connect(f"/service/ws?token={TEST_TOKEN}") as ws2:
        _send(ws1, {"reqId": "j1", "op": "room.join", "data": {"roomId": "room-1"}})
        _send(ws2, {"reqId": "j2", "op": "room.join", "data": {"roomId": "room-1"}})
        j1 = _recv(ws1)
        j2 = _recv(ws2)
        assert j1["event"] == "result"
        assert j2["event"] == "result"

        _send(ws1, {"reqId": "t1", "op": "room.typing", "data": {"roomId": "room-1", "userId": "u-1"}})
        # Sender gets ack
        ack = _recv(ws1)
        assert ack["event"] == "ack" and ack["op"] == "room.typing"
        # Other client gets broadcast update
        upd = _recv(ws2)
        assert upd["op"] == "room.typing"
        assert upd["event"] == "update"
        assert upd["roomId"] == "room-1"


if __name__ == "__main__":
    # 允许 `python tests/test_service_ws.py` 直接运行，仅输出：
    #   - 每个测试一次 “<用例名>：验证通过”
    #   - 最后一行汇总 “WS 网关测试：验证通过✅/失败❌”
    import os
    import contextlib
    import sys as _sys

    class _MinimalCNReporter:
        def __init__(self):
            self.failed = 0

        def pytest_runtest_logreport(self, report):
            if report.when != "call":
                return
            name = report.nodeid.split("::")[-1]
            if report.passed:
                _sys.__stdout__.write(f"{name}：验证通过\n")
            elif report.failed:
                self.failed += 1
                _sys.__stdout__.write(f"{name}：验证失败\n")

    # 静音 pytest 自身输出与第三方告警，仅保留自定义中文提示
    args = [__file__, "-q", "-p", "no:warnings"]
    plugin = _MinimalCNReporter()
    try:
        with contextlib.redirect_stdout(open(os.devnull, "w")), contextlib.redirect_stderr(open(os.devnull, "w")):
            code = pytest.main(args, plugins=[plugin])
    except SystemExit as e:
        code = int(getattr(e, "code", 1) or 0)

    if code == 0:
        print("WS 网关测试：验证通过✅")
    else:
        print("WS 网关测试：验证失败❌ (exit=", code, ")", sep="")
    raise SystemExit(code)
