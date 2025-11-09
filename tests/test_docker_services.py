"""Docker services connectivity tests (HTTP/WS/Ports) with minimal CN output.

This focuses on service health/connectivity, not LLM functionality.
Environment overrides (optional):
  - TEST_BASE_URL (default: http://localhost:8000)
  - TEST_WS_URL   (default: ws(s)://<host>/service/ws derived from BASE_URL)
  - TEST_REDIS_HOST / TEST_REDIS_PORT (default: localhost / 6379)
  - TEST_DB_HOST    / TEST_DB_PORT    (default: localhost / 5432)
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import ssl
import struct
import sys
import time
import urllib.parse
import warnings

import pytest


warnings.filterwarnings("ignore")


def _env(name: str, default: str) -> str:
    v = os.environ.get(name)
    return v if v else default


BASE_URL = _env("TEST_BASE_URL", "http://localhost:8000")
WS_URL = os.environ.get("TEST_WS_URL")
if not WS_URL:
    p = urllib.parse.urlparse(BASE_URL)
    scheme = "wss" if p.scheme == "https" else "ws"
    WS_URL = f"{scheme}://{p.hostname or 'localhost'}:{p.port or (443 if scheme=='wss' else 8000)}/service/ws"

REDIS_HOST = _env("TEST_REDIS_HOST", "localhost")
REDIS_PORT = int(_env("TEST_REDIS_PORT", "6379"))
DB_HOST = _env("TEST_DB_HOST", "localhost")
DB_PORT = int(_env("TEST_DB_PORT", "5432"))


def _http_get(url: str, timeout: float = 5.0) -> int:
    # Try urllib only (avoid external deps)
    import urllib.request

    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.getcode()  # type: ignore[no-any-return]


def _tcp_check(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _ws_connect(url: str, timeout: float = 5.0) -> socket.socket:
    # Minimal RFC6455 client: ws/wss handshake only
    u = urllib.parse.urlparse(url)
    assert u.scheme in {"ws", "wss"}
    host = u.hostname or "localhost"
    port = u.port or (443 if u.scheme == "wss" else 80)
    path = u.path or "/"
    if u.query:
        path += "?" + u.query

    raw = socket.create_connection((host, port), timeout=timeout)
    if u.scheme == "wss":
        ctx = ssl.create_default_context()
        raw = ctx.wrap_socket(raw, server_hostname=host)

    key = base64.b64encode(os.urandom(16)).decode()
    headers = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n\r\n"
    ).encode()
    raw.sendall(headers)

    # Read HTTP response
    raw.settimeout(timeout)
    buff = b""
    while b"\r\n\r\n" not in buff:
        chunk = raw.recv(4096)
        if not chunk:
            break
        buff += chunk
    if b" 101 " not in buff.split(b"\r\n", 1)[0]:
        raise RuntimeError(f"WS handshake failed: {buff.splitlines()[:1]}")
    return raw


def _ws_send_text(sock: socket.socket, text: str) -> None:
    payload = text.encode("utf-8")
    fin_opcode = 0x81  # FIN=1, text frame
    mask_bit = 0x80
    length = len(payload)
    header = bytearray([fin_opcode])
    if length < 126:
        header.append(mask_bit | length)
    elif length < (1 << 16):
        header.append(mask_bit | 126)
        header.extend(struct.pack("!H", length))
    else:
        header.append(mask_bit | 127)
        header.extend(struct.pack("!Q", length))
    mask = os.urandom(4)
    header.extend(mask)
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    sock.sendall(header + masked)


def _ws_recv_text(sock: socket.socket, timeout: float = 5.0) -> str | None:
    sock.settimeout(timeout)
    # Read first 2 bytes header
    hdr = sock.recv(2)
    if len(hdr) < 2:
        return None
    b1, b2 = hdr[0], hdr[1]
    fin = (b1 & 0x80) != 0
    opcode = b1 & 0x0F
    masked = (b2 & 0x80) != 0
    length = b2 & 0x7F
    if length == 126:
        ext = sock.recv(2)
        length = struct.unpack("!H", ext)[0]
    elif length == 127:
        ext = sock.recv(8)
        length = struct.unpack("!Q", ext)[0]
    mask_key = b""
    if masked:
        mask_key = sock.recv(4)
    payload = b""
    while len(payload) < length:
        chunk = sock.recv(length - len(payload))
        if not chunk:
            break
        payload += chunk
    if masked and mask_key:
        payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
    if opcode == 0x8:  # close
        return None
    if opcode != 0x1:  # not text
        return None
    return payload.decode("utf-8", errors="ignore")


@pytest.mark.timeout(10)
def test_app_http_ping():
    code = _http_get(f"{BASE_URL}/ping", timeout=5.0)
    assert code == 200


@pytest.mark.timeout(10)
def test_app_ws_gateway_ping():
    s = _ws_connect(WS_URL, timeout=5.0)
    try:
        _ws_send_text(s, json.dumps({"reqId": "r-py", "op": "ping"}, ensure_ascii=False))
        deadline = time.time() + 5.0
        buf = ""
        while time.time() < deadline:
            msg = _ws_recv_text(s, timeout=1.0)
            if not msg:
                continue
            buf += msg
            try:
                data = json.loads(buf)
                if (
                    isinstance(data, dict)
                    and data.get("op") == "ping"
                    and data.get("event") == "pong"
                ):
                    return
            except json.JSONDecodeError:
                # Keep accumulating in case of partial frame split (rare)
                pass
        pytest.fail("WS ping timeout")
    finally:
        try:
            s.close()
        except Exception:
            pass


@pytest.mark.timeout(5)
def test_redis_port():
    assert _tcp_check(REDIS_HOST, REDIS_PORT, timeout=2.0)


@pytest.mark.timeout(5)
def test_postgres_port():
    assert _tcp_check(DB_HOST, DB_PORT, timeout=2.0)


if __name__ == "__main__":
    # Minimal per-test CN output + final summary
    import contextlib

    class _MinimalCNReporter:
        def __init__(self):
            self.failed = 0

        def pytest_runtest_logreport(self, report):
            if report.when != "call":
                return
            name = report.nodeid.split("::")[-1]
            if report.passed:
                sys.__stdout__.write(f"{name}：验证通过\n")
            elif report.failed:
                self.failed += 1
                sys.__stdout__.write(f"{name}：验证失败\n")

    args = [__file__, "-q", "-p", "no:warnings"]
    plugin = _MinimalCNReporter()
    try:
        with contextlib.redirect_stdout(open(os.devnull, "w")), contextlib.redirect_stderr(open(os.devnull, "w")):
            code = pytest.main(args, plugins=[plugin])
    except SystemExit as e:
        code = int(getattr(e, "code", 1) or 0)

    if code == 0:
        print("Docker 服务联通性：验证通过✅")
    else:
        print(f"Docker 服务联通性：验证失败❌ (exit={code})")
    raise SystemExit(code)

