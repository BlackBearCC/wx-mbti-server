"""HTTP tests for /service/chat and /service/streamchat with minimal CN output.

These tests override the AI dependency to avoid real network calls.
Running directly (python tests/test_service_http.py) prints only per-test
and a final summary in Chinese.
"""
import sys
import warnings
from typing import AsyncIterator

import pytest
from starlette.testclient import TestClient

warnings.filterwarnings("ignore")

from app.main import app  # noqa: E402
from app.services.ai import get_ai_service  # noqa: E402
from app.services.ai.providers.base import AIChatResponse  # noqa: E402


class _FakeAIService:
    async def chat(self, **kwargs) -> AIChatResponse:
        return AIChatResponse(
            text="http fake resp",
            model="fake-model-http",
            usage={"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
        )

    async def stream_chat(self, **kwargs) -> AsyncIterator[str]:
        for c in ("a", "b", "c"):
            yield c


@pytest.fixture()
def client():
    async def _override():
        return _FakeAIService()

    app.dependency_overrides[get_ai_service] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_ai_service, None)


def test_http_chat_ok(client: TestClient):
    resp = client.post(
        "/service/chat",
        json={
            "modelAlias": "default",
            "messages": [{"role": "user", "content": "hi"}],
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["text"] == "http fake resp"
    assert body["data"]["model"] == "fake-model-http"


def test_http_streamchat_sse(client: TestClient):
    with client.stream(
        "POST",
        "/service/streamchat",
        json={
            "modelAlias": "default",
            "messages": [{"role": "user", "content": "stream"}],
        },
    ) as s:
        chunks = []
        for line in s.iter_lines():
            if not line:
                continue
            if line == "data: [DONE]":
                break
            assert line.startswith("data: ")
            chunks.append(line[len("data: ") :])
        assert "".join(chunks) == "abc"


if __name__ == "__main__":
    # Run via pytest but print minimal CN output per test + final summary.
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

    args = [__file__, "-q", "-p", "no:warnings"]
    plugin = _MinimalCNReporter()
    try:
        with contextlib.redirect_stdout(open(os.devnull, "w")), contextlib.redirect_stderr(open(os.devnull, "w")):
            code = pytest.main(args, plugins=[plugin])
    except SystemExit as e:
        code = int(getattr(e, "code", 1) or 0)

    if code == 0:
        print("HTTP 服务测试：验证通过✅")
    else:
        print("HTTP 服务测试：验证失败❌ (exit=", code, ")", sep="")
    raise SystemExit(code)

