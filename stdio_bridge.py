#!/usr/bin/env python3
"""
stdio ↔ TCP 브릿지
OpenCode(stdio) → 이 스크립트 → sysinfo_server.py(TCP 8891)
"""

import sys
import socket
import subprocess
import time
import os
import json

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8891
SERVER_SCRIPT = os.path.join(os.path.dirname(__file__), "sysinfo_server.py")

def start_server():
    try:
        s = socket.create_connection((SERVER_HOST, SERVER_PORT), timeout=1)
        s.close()
    except (ConnectionRefusedError, OSError):
        subprocess.Popen(
            [sys.executable, SERVER_SCRIPT],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(1.0)

def recv_line(sock, buf):
    """소켓에서 줄바꿈까지 읽기"""
    while "\n" not in buf:
        chunk = sock.recv(4096).decode("utf-8")
        if not chunk:
            raise ConnectionError("서버 연결 끊김")
        buf += chunk
    line, buf = buf.split("\n", 1)
    return line.strip(), buf

def main():
    start_server()
    sock = socket.create_connection((SERVER_HOST, SERVER_PORT))
    buf = ""

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        # 서버로 전달
        sock.sendall((line + "\n").encode("utf-8"))

        # 알림(notification)은 서버가 응답 안 함 → stdout에도 쓰지 않음
        try:
            msg = json.loads(line)
            if "id" not in msg:
                continue
        except json.JSONDecodeError:
            continue

        # 응답 읽어서 stdout으로
        resp, buf = recv_line(sock, buf)
        sys.stdout.write(resp + "\n")
        sys.stdout.flush()

    sock.close()

if __name__ == "__main__":
    main()
