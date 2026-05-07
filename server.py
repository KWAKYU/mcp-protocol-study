#!/usr/bin/env python3
"""
MCP Server (TCP transport) — nc로 직접 연결해서 프로토콜 실습 가능
포트 8888에서 연결을 기다림

nc localhost 8888 으로 직접 JSON-RPC 메시지를 보낼 수 있음
"""

import socket
import json
import sys
import threading
import datetime

HOST = "127.0.0.1"
PORT = 8888

# ── 도구 구현 ──────────────────────────────────────────────────────────────

def tool_echo(params: dict) -> str:
    message = params.get("message", "")
    return f"Echo: {message}"

def tool_add(params: dict) -> str:
    a = params.get("a", 0)
    b = params.get("b", 0)
    return f"{a} + {b} = {a + b}"

def tool_time(params: dict) -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

TOOLS = {
    "echo": {
        "name": "echo",
        "description": "메시지를 그대로 돌려줌",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "돌려줄 메시지"}
            },
            "required": ["message"]
        }
    },
    "add": {
        "name": "add",
        "description": "두 수를 더함",
        "inputSchema": {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "첫 번째 수"},
                "b": {"type": "number", "description": "두 번째 수"}
            },
            "required": ["a", "b"]
        }
    },
    "time": {
        "name": "time",
        "description": "현재 시각을 반환",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    }
}

TOOL_HANDLERS = {
    "echo": tool_echo,
    "add": tool_add,
    "time": tool_time,
}

# ── JSON-RPC 응답 헬퍼 ────────────────────────────────────────────────────

def ok(id_, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "result": result}

def err(id_, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}

# ── MCP 메시지 처리 ───────────────────────────────────────────────────────

def handle_message(raw: str) -> dict | None:
    """JSON-RPC 메시지 하나를 받아 응답 dict 또는 None(알림은 응답 없음)을 반환"""
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError as e:
        return err(None, -32700, f"Parse error: {e}")

    method = msg.get("method", "")
    id_ = msg.get("id")          # 알림(notification)이면 id 없음
    params = msg.get("params", {})

    print(f"  ← method={method!r}  id={id_}", flush=True)

    # ── initialize ────────────────────────────────────────────────────────
    if method == "initialize":
        return ok(id_, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "mcp-learn-server", "version": "1.0.0"}
        })

    # ── initialized (알림 — 응답 없음) ───────────────────────────────────
    if method == "notifications/initialized":
        print("  ✓ 클라이언트 초기화 완료", flush=True)
        return None

    # ── tools/list ────────────────────────────────────────────────────────
    if method == "tools/list":
        return ok(id_, {"tools": list(TOOLS.values())})

    # ── tools/call ────────────────────────────────────────────────────────
    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments", {})
        if name not in TOOL_HANDLERS:
            return err(id_, -32601, f"Unknown tool: {name!r}")
        try:
            result_text = TOOL_HANDLERS[name](args)
            return ok(id_, {
                "content": [{"type": "text", "text": result_text}],
                "isError": False
            })
        except Exception as e:
            return err(id_, -32603, str(e))

    # ── ping ──────────────────────────────────────────────────────────────
    if method == "ping":
        return ok(id_, {})

    # ── 알 수 없는 메서드 ─────────────────────────────────────────────────
    if id_ is not None:
        return err(id_, -32601, f"Method not found: {method!r}")
    return None  # 알 수 없는 알림은 무시

# ── 클라이언트 연결 처리 ──────────────────────────────────────────────────

def handle_client(conn: socket.socket, addr):
    print(f"\n[+] 연결됨: {addr}", flush=True)
    buf = ""
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break
            buf += data.decode("utf-8", errors="replace")

            # 줄바꿈 단위로 메시지 분리 (newline-delimited JSON)
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                response = handle_message(line)
                if response is not None:
                    out = json.dumps(response, ensure_ascii=False) + "\n"
                    print(f"  → {out.rstrip()}", flush=True)
                    conn.sendall(out.encode("utf-8"))
    except ConnectionResetError:
        pass
    finally:
        conn.close()
        print(f"[-] 연결 종료: {addr}", flush=True)

# ── 메인 ──────────────────────────────────────────────────────────────────

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"MCP 학습 서버 시작 — {HOST}:{PORT}")
    print("nc로 연결: nc localhost 8888")
    print("-" * 50)
    try:
        while True:
            conn, addr = server.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print("\n서버 종료")
    finally:
        server.close()

if __name__ == "__main__":
    main()
