#!/usr/bin/env python3
"""
MCP Client — server.py에 연결해서 도구 목록 조회 및 호출을 순서대로 시연

실행: python client.py [--verbose]
  --verbose  주고받는 원시 JSON을 그대로 출력
"""

import socket
import json
import sys

HOST = "127.0.0.1"
PORT = 8888
VERBOSE = "--verbose" in sys.argv

_id_counter = 0

def next_id() -> int:
    global _id_counter
    _id_counter += 1
    return _id_counter


class MCPClient:
    def __init__(self, host: str, port: int):
        self.sock = socket.create_connection((host, port))
        self.buf = ""

    # ── 저수준 송수신 ─────────────────────────────────────────────────────

    def _send(self, msg: dict):
        raw = json.dumps(msg, ensure_ascii=False) + "\n"
        if VERBOSE:
            print(f"SEND → {raw.rstrip()}")
        self.sock.sendall(raw.encode("utf-8"))

    def _recv(self) -> dict:
        """응답 한 줄(JSON)을 읽어 dict로 반환"""
        while "\n" not in self.buf:
            chunk = self.sock.recv(4096).decode("utf-8")
            if not chunk:
                raise ConnectionError("서버 연결 끊김")
            self.buf += chunk
        line, self.buf = self.buf.split("\n", 1)
        if VERBOSE:
            print(f"RECV ← {line.rstrip()}")
        return json.loads(line)

    # ── JSON-RPC 헬퍼 ─────────────────────────────────────────────────────

    def request(self, method: str, params: dict = {}) -> dict:
        id_ = next_id()
        self._send({"jsonrpc": "2.0", "id": id_, "method": method, "params": params})
        return self._recv()

    def notify(self, method: str, params: dict = {}):
        """알림(notification) — id 없음, 응답 없음"""
        self._send({"jsonrpc": "2.0", "method": method, "params": params})

    def close(self):
        self.sock.close()

    # ── MCP 고수준 메서드 ─────────────────────────────────────────────────

    def initialize(self) -> dict:
        resp = self.request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "learn-client", "version": "1.0"}
        })
        # 핸드셰이크 완료 알림 전송
        self.notify("notifications/initialized")
        return resp

    def list_tools(self) -> list:
        resp = self.request("tools/list")
        return resp.get("result", {}).get("tools", [])

    def call_tool(self, name: str, arguments: dict = {}) -> str:
        resp = self.request("tools/call", {"name": name, "arguments": arguments})
        result = resp.get("result", {})
        content = result.get("content", [])
        return " | ".join(c.get("text", "") for c in content)

    def ping(self) -> bool:
        resp = self.request("ping")
        return "result" in resp


# ── 시연 시나리오 ──────────────────────────────────────────────────────────

def demo():
    print("=" * 55)
    print("  MCP 학습 클라이언트")
    print("=" * 55)

    client = MCPClient(HOST, PORT)

    # 1. 핸드셰이크
    print("\n[1] initialize 핸드셰이크")
    resp = client.initialize()
    info = resp.get("result", {}).get("serverInfo", {})
    caps = resp.get("result", {}).get("capabilities", {})
    print(f"    서버: {info.get('name')} v{info.get('version')}")
    print(f"    capabilities: {list(caps.keys())}")

    # 2. ping
    print("\n[2] ping")
    ok = client.ping()
    print(f"    응답: {'pong ✓' if ok else '실패'}")

    # 3. 도구 목록
    print("\n[3] tools/list")
    tools = client.list_tools()
    for t in tools:
        print(f"    • {t['name']}: {t['description']}")

    # 4. 도구 호출
    print("\n[4] tools/call — echo")
    result = client.call_tool("echo", {"message": "안녕, MCP!"})
    print(f"    결과: {result}")

    print("\n[5] tools/call — add")
    result = client.call_tool("add", {"a": 7, "b": 13})
    print(f"    결과: {result}")

    print("\n[6] tools/call — time")
    result = client.call_tool("time")
    print(f"    결과: {result}")

    client.close()
    print("\n완료.")

if __name__ == "__main__":
    demo()
