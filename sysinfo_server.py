#!/usr/bin/env python3
"""
시스템 정보 MCP 서버 (포트 8891)
툴: cpu, memory, battery, disk, processes, open_dashboard
"""

import socket
import json
import threading
import subprocess
import os
import sys

HOST = "127.0.0.1"
PORT = 8891

# ── 툴 구현 ────────────────────────────────────────────────────────────────

def tool_cpu(params):
    result = subprocess.run(["top", "-l", "1", "-n", "0"], capture_output=True, text=True)
    for line in result.stdout.splitlines():
        if "CPU usage" in line:
            return line.strip()
    return "CPU 정보 없음"

def tool_memory(params):
    result = subprocess.run(["vm_stat"], capture_output=True, text=True)
    stats = {}
    for line in result.stdout.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            stats[k.strip()] = v.strip().rstrip(".")

    page = 4096
    def mb(key):
        return int(stats.get(key, "0").replace(",", "")) * page // (1024 ** 2)

    free   = mb("Pages free")
    active = mb("Pages active")
    wired  = mb("Pages wired down")
    inactive = mb("Pages inactive")
    total  = free + active + wired + inactive
    used   = active + wired

    return (
        f"전체:    {total} MB\n"
        f"사용 중: {used} MB\n"
        f"여유:    {free} MB\n"
        f"사용률:  {used * 100 // total if total else 0}%"
    )

def tool_battery(params):
    result = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True)
    lines = result.stdout.strip().splitlines()
    if len(lines) >= 2:
        return lines[1].strip()
    return "배터리 정보 없음 (데스크탑일 수 있음)"

def tool_disk(params):
    result = subprocess.run(["df", "-h", "/"], capture_output=True, text=True)
    lines = result.stdout.strip().splitlines()
    if len(lines) >= 2:
        parts = lines[1].split()
        return (
            f"전체:    {parts[1]}\n"
            f"사용 중: {parts[2]}\n"
            f"여유:    {parts[3]}\n"
            f"사용률:  {parts[4]}"
        )
    return "디스크 정보 없음"

_dashboard_started = False

def tool_open_dashboard(params):
    global _dashboard_started
    dashboard_path = os.path.join(os.path.dirname(__file__), "dashboard.py")
    if not _dashboard_started:
        subprocess.Popen([sys.executable, dashboard_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        _dashboard_started = True
        import time; time.sleep(0.8)
    subprocess.run(["open", "http://127.0.0.1:8892"])
    return "대시보드를 브라우저에서 열었습니다 → http://127.0.0.1:8892"

def tool_processes(params):
    n = int(params.get("n", 5))
    result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
    procs = []
    for line in result.stdout.splitlines()[1:]:
        parts = line.split(None, 10)
        if len(parts) >= 11:
            try:
                procs.append((float(parts[2]), parts[10][:45]))
            except ValueError:
                pass
    procs.sort(reverse=True)
    lines = ["CPU%    프로세스"]
    for cpu, name in procs[:n]:
        lines.append(f"{cpu:5.1f}%  {name}")
    return "\n".join(lines)

# ── 툴 등록 ────────────────────────────────────────────────────────────────

TOOLS = {
    "cpu": {
        "name": "cpu",
        "description": "현재 CPU 사용률",
        "inputSchema": {"type": "object", "properties": {}}
    },
    "memory": {
        "name": "memory",
        "description": "메모리 사용량",
        "inputSchema": {"type": "object", "properties": {}}
    },
    "battery": {
        "name": "battery",
        "description": "배터리 잔량 및 충전 상태",
        "inputSchema": {"type": "object", "properties": {}}
    },
    "disk": {
        "name": "disk",
        "description": "디스크 사용량",
        "inputSchema": {"type": "object", "properties": {}}
    },
    "processes": {
        "name": "processes",
        "description": "CPU 많이 쓰는 프로세스 목록",
        "inputSchema": {
            "type": "object",
            "properties": {
                "n": {"type": "number", "description": "몇 개 볼지 (기본 5)"}
            }
        }
    },
    "open_dashboard": {
        "name": "open_dashboard",
        "description": "시스템 정보 대시보드를 브라우저로 열기",
        "inputSchema": {"type": "object", "properties": {}}
    },
}

TOOL_HANDLERS = {
    "cpu":            tool_cpu,
    "memory":         tool_memory,
    "battery":        tool_battery,
    "disk":           tool_disk,
    "processes":      tool_processes,
    "open_dashboard": tool_open_dashboard,
}

# ── JSON-RPC ───────────────────────────────────────────────────────────────

def ok(id_, result): return {"jsonrpc": "2.0", "id": id_, "result": result}
def err(id_, code, msg): return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": msg}}

def handle(raw):
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError as e:
        return err(None, -32700, f"Parse error: {e}")

    method = msg.get("method", "")
    id_    = msg.get("id")
    params = msg.get("params", {})

    print(f"  ← {method}  id={id_}", flush=True)

    if method == "initialize":
        return ok(id_, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "sysinfo-mcp-server", "version": "1.0.0"}
        })
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return ok(id_, {"tools": list(TOOLS.values())})
    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments", {})
        if name not in TOOL_HANDLERS:
            return err(id_, -32601, f"Unknown tool: {name!r}")
        try:
            text = TOOL_HANDLERS[name](args)
            return ok(id_, {"content": [{"type": "text", "text": text}], "isError": False})
        except Exception as e:
            return err(id_, -32603, str(e))
    if method == "ping":
        return ok(id_, {})
    if id_ is not None:
        return err(id_, -32601, f"Method not found: {method!r}")
    return None

# ── 소켓 서버 ──────────────────────────────────────────────────────────────

def handle_client(conn, addr):
    print(f"\n[+] 연결: {addr}", flush=True)
    buf = ""
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break
            buf += data.decode("utf-8", errors="replace")
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                resp = handle(line)
                if resp:
                    out = json.dumps(resp, ensure_ascii=False) + "\n"
                    print(f"  → {out.rstrip()}", flush=True)
                    conn.sendall(out.encode())
    except ConnectionResetError:
        pass
    finally:
        conn.close()
        print(f"[-] 종료: {addr}", flush=True)

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(5)
    print(f"시스템 정보 MCP 서버 — {HOST}:{PORT}")
    print("툴: cpu / memory / battery / disk / processes")
    print("-" * 50)
    try:
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()
    except KeyboardInterrupt:
        print("\n종료")
    finally:
        s.close()

if __name__ == "__main__":
    main()
