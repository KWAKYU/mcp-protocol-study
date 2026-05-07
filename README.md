# MCP 프로토콜 학습 실습

MCP(Model Context Protocol)가 실제로 어떤 JSON을 주고받는지  
`nc`(netcat)로 직접 보면서 이해하는 실습 프로젝트입니다.

## 파일 구조

```
├── server.py         # 기본 MCP 서버 (echo, add, time 툴) — 포트 8888
├── client.py         # Python MCP 클라이언트 (--verbose로 원시 JSON 확인)
└── sysinfo_server.py # 시스템 정보 MCP 서버 (cpu, memory, battery, disk, processes) — 포트 8891
```

## 실행 방법

### 기본 서버

```bash
# 터미널 1
python server.py

# 터미널 2
python client.py --verbose
```

### nc로 직접 프로토콜 확인

```bash
# 터미널 1
python server.py

# 터미널 2
nc localhost 8888
```

이후 JSON을 한 줄씩 입력:

```
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"me","version":"1"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"add","arguments":{"a":3,"b":4}}}
```

### 시스템 정보 서버

```bash
# 터미널 1
python sysinfo_server.py

# 터미널 2
nc localhost 8891
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"me","version":"1"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"battery","arguments":{}}}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"cpu","arguments":{}}}
```

## MCP 프로토콜 흐름

```
클라이언트                        서버
   │── initialize ──────────────→ │
   │←──────────── initialize ok ──│
   │── notifications/initialized → │  (응답 없음)
   │── tools/list ──────────────→ │
   │←────────────────── [tools] ──│
   │── tools/call ─────────────→  │
   │←────────────────── 결과 ─────│
```

### 메시지 구조

| 구분 | 조건 | 설명 |
|---|---|---|
| 요청 | `id` 있음 | 서버가 반드시 응답 |
| 알림 | `id` 없음 | 서버가 응답하지 않음 |
| 성공 응답 | `result` 있음 | 정상 처리 |
| 에러 응답 | `error` 있음 | 실패 (code로 원인 구분) |

### 에러 코드

| 코드 | 의미 |
|---|---|
| `-32700` | JSON 파싱 실패 |
| `-32601` | 존재하지 않는 메서드/툴 |
| `-32603` | 서버 내부 에러 |

## 제공 툴

### server.py (포트 8888)

| 툴 | 설명 |
|---|---|
| `echo` | 메시지를 그대로 반환 |
| `add` | 두 수를 더함 |
| `time` | 현재 시각 반환 |

### sysinfo_server.py (포트 8891)

| 툴 | 설명 |
|---|---|
| `cpu` | CPU 사용률 |
| `memory` | 메모리 사용량 |
| `battery` | 배터리 잔량 및 충전 상태 |
| `disk` | 디스크 사용량 |
| `processes` | CPU 상위 프로세스 목록 |

## 표준 MCP와의 차이

표준 MCP는 `stdio` 기반이지만, 이 실습은 `nc`로 직접 연결해서 JSON을 볼 수 있도록 **TCP 소켓**을 사용했습니다. 메시지 형식(JSON-RPC 2.0)은 동일합니다.
