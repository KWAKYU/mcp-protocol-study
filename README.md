# MCP 시스템 정보 서버

MCP(Model Context Protocol)를 활용해 맥북의 실시간 시스템 정보를 제공하는 서버입니다.

## 실행 방법

```bash
python sysinfo_server.py
```

### nc로 직접 연결

```bash
nc localhost 8891
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"me","version":"1"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"battery","arguments":{}}}
```

## 제공 툴 (포트 8891)

| 툴 | 설명 |
|---|---|
| `cpu` | CPU 사용률 |
| `memory` | 메모리 사용량 |
| `battery` | 배터리 잔량 및 충전 상태 |
| `disk` | 디스크 사용량 |
| `processes` | CPU 상위 프로세스 목록 (`n`으로 개수 지정, 기본 5) |

## 실행 예시

```
━━━  CPU
CPU usage: 6.45% user, 14.40% sys, 79.13% idle

━━━  메모리
전체:    1158 MB
사용 중: 711 MB
여유:    107 MB
사용률:  61%

━━━  배터리
-InternalBattery-0	84%; discharging; 8:15 remaining

━━━  디스크
전체:    228Gi
사용 중: 12Gi
여유:    127Gi
사용률:  9%

━━━  CPU 상위 프로세스 5개
CPU%    프로세스
 24.1%  /System/Library/PrivateFrameworks/SkyLight.fr
 11.4%  /Applications/Claude.app/Contents/Frameworks/
  7.7%  /Applications/Claude.app/Contents/Frameworks/
  3.8%  /usr/sbin/bluetoothd
  1.7%  /usr/libexec/locationd
```
