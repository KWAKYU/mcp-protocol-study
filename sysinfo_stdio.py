#!/usr/bin/env python3
"""
시스템 정보 MCP 서버 — stdio 버전
OpenCode에서 직접 사용 가능
"""

import sys
import json
import subprocess
import os

def get_cpu():
    r = subprocess.run(["top", "-l", "1", "-n", "0"], capture_output=True, text=True)
    for line in r.stdout.splitlines():
        if "CPU usage" in line:
            return line.strip()
    return "N/A"

def get_memory():
    r = subprocess.run(["vm_stat"], capture_output=True, text=True)
    stats = {}
    for line in r.stdout.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            stats[k.strip()] = v.strip().rstrip(".")
    page = 4096
    def mb(key): return int(stats.get(key, "0").replace(",", "")) * page // (1024 ** 2)
    free = mb("Pages free")
    active = mb("Pages active")
    wired = mb("Pages wired down")
    total = free + active + wired + mb("Pages inactive")
    used = active + wired
    return f"전체: {total} MB\n사용 중: {used} MB\n여유: {free} MB\n사용률: {used * 100 // total if total else 0}%"

def get_battery():
    r = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True)
    lines = r.stdout.strip().splitlines()
    return lines[1].strip() if len(lines) >= 2 else "N/A"

def get_disk():
    r = subprocess.run(["df", "-h", "/"], capture_output=True, text=True)
    lines = r.stdout.strip().splitlines()
    if len(lines) >= 2:
        p = lines[1].split()
        return f"전체: {p[1]}\n사용 중: {p[2]}\n여유: {p[3]}\n사용률: {p[4]}"
    return "N/A"

def get_processes(n=5):
    r = subprocess.run(["ps", "aux"], capture_output=True, text=True)
    procs = []
    for line in r.stdout.splitlines()[1:]:
        parts = line.split(None, 10)
        if len(parts) >= 11:
            try:
                procs.append((float(parts[2]), parts[10].split("/")[-1][:40]))
            except ValueError:
                pass
    procs.sort(reverse=True)
    lines = ["CPU%    프로세스"]
    for cpu, name in procs[:n]:
        lines.append(f"{cpu:5.1f}%  {name}")
    return "\n".join(lines)

def open_dashboard():
    dashboard = os.path.join(os.path.dirname(__file__), "dashboard.py")
    import subprocess as sp, sys as _sys, time
    sp.Popen([_sys.executable, dashboard], stdout=sp.DEVNULL, stderr=sp.DEVNULL)
    time.sleep(0.8)
    sp.run(["open", "http://127.0.0.1:8892"])
    return "대시보드 열림 → http://127.0.0.1:8892"

TOOLS = [
    {"name": "cpu",            "description": "현재 CPU 사용률",              "inputSchema": {"type": "object", "properties": {}}},
    {"name": "memory",         "description": "메모리 사용량",                "inputSchema": {"type": "object", "properties": {}}},
    {"name": "battery",        "description": "배터리 잔량 및 충전 상태",      "inputSchema": {"type": "object", "properties": {}}},
    {"name": "disk",           "description": "디스크 사용량",                "inputSchema": {"type": "object", "properties": {}}},
    {"name": "processes",      "description": "CPU 많이 쓰는 프로세스 목록",   "inputSchema": {"type": "object", "properties": {"n": {"type": "number", "description": "몇 개 볼지 (기본 5)"}}}},
    {"name": "open_dashboard", "description": "시스템 정보 대시보드를 브라우저로 열기", "inputSchema": {"type": "object", "properties": {}}},
]

HANDLERS = {
    "cpu":            lambda a: get_cpu(),
    "memory":         lambda a: get_memory(),
    "battery":        lambda a: get_battery(),
    "disk":           lambda a: get_disk(),
    "processes":      lambda a: get_processes(int(a.get("n", 5))),
    "open_dashboard": lambda a: open_dashboard(),
}

def ok(id_, result): return {"jsonrpc": "2.0", "id": id_, "result": result}
def err(id_, code, msg): return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": msg}}

def send(msg):
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()

def handle(raw):
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError as e:
        return err(None, -32700, str(e))

    method = msg.get("method", "")
    id_    = msg.get("id")
    params = msg.get("params", {})

    if method == "initialize":
        return ok(id_, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "sysinfo-mcp-server", "version": "1.0.0"}
        })
    if method == "notifications/initialized":
        return None
    if method == "tools/list":
        return ok(id_, {"tools": TOOLS})
    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments", {})
        if name not in HANDLERS:
            return err(id_, -32601, f"Unknown tool: {name!r}")
        try:
            text = HANDLERS[name](args)
            return ok(id_, {"content": [{"type": "text", "text": text}], "isError": False})
        except Exception as e:
            return err(id_, -32603, str(e))
    if method == "ping":
        return ok(id_, {})
    if id_ is not None:
        return err(id_, -32601, f"Method not found: {method!r}")
    return None

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    resp = handle(line)
    if resp is not None:
        send(resp)
