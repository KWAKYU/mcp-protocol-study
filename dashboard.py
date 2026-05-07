#!/usr/bin/env python3
"""
시스템 정보 대시보드 웹 서버 (포트 8892)
MCP sysinfo_server의 open_dashboard 툴이 이 서버를 띄우고 브라우저를 엽니다.
"""

import subprocess
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8892

# ── 시스템 정보 수집 ───────────────────────────────────────────────────────

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
    inactive = mb("Pages inactive")
    total = free + active + wired + inactive
    used = active + wired
    return {"total": total, "used": used, "free": free, "pct": used * 100 // total if total else 0}

def get_battery():
    r = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True)
    lines = r.stdout.strip().splitlines()
    if len(lines) >= 2:
        return lines[1].strip()
    return "N/A"

def get_disk():
    r = subprocess.run(["df", "-h", "/"], capture_output=True, text=True)
    lines = r.stdout.strip().splitlines()
    if len(lines) >= 2:
        p = lines[1].split()
        return {"total": p[1], "used": p[2], "free": p[3], "pct": p[4]}
    return {}

def get_processes():
    r = subprocess.run(["ps", "aux"], capture_output=True, text=True)
    procs = []
    for line in r.stdout.splitlines()[1:]:
        parts = line.split(None, 10)
        if len(parts) >= 11:
            try:
                name = parts[10].split("/")[-1][:30]
                procs.append({"cpu": float(parts[2]), "name": name})
            except ValueError:
                pass
    procs.sort(key=lambda x: x["cpu"], reverse=True)
    return procs[:5]

# ── HTTP 핸들러 ────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass  # 로그 끄기

    def do_GET(self):
        if self.path == "/api":
            data = {
                "cpu": get_cpu(),
                "memory": get_memory(),
                "battery": get_battery(),
                "disk": get_disk(),
                "processes": get_processes(),
            }
            body = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        elif self.path == "/" or self.path == "/index.html":
            html = HTML.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html)
        else:
            self.send_response(404)
            self.end_headers()

# ── HTML ───────────────────────────────────────────────────────────────────

HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>System Info</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    background: #0f0f0f;
    color: #e0e0e0;
    min-height: 100vh;
    padding: 32px 24px;
  }
  h1 {
    font-size: 18px;
    font-weight: 600;
    color: #fff;
    margin-bottom: 24px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 16px;
    margin-bottom: 16px;
  }
  .card {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 12px;
    padding: 20px;
  }
  .card-title {
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #666;
    margin-bottom: 12px;
  }
  .card-value {
    font-size: 28px;
    font-weight: 700;
    color: #fff;
    line-height: 1;
    margin-bottom: 8px;
  }
  .card-sub {
    font-size: 12px;
    color: #555;
    line-height: 1.6;
  }
  .bar-wrap {
    background: #2a2a2a;
    border-radius: 4px;
    height: 6px;
    margin-top: 12px;
    overflow: hidden;
  }
  .bar {
    height: 100%;
    border-radius: 4px;
    background: #4ade80;
    transition: width 0.5s ease;
  }
  .bar.warn { background: #facc15; }
  .bar.danger { background: #f87171; }
  .proc-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 0;
    border-bottom: 1px solid #222;
    font-size: 12px;
  }
  .proc-row:last-child { border-bottom: none; }
  .proc-name { color: #aaa; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .proc-cpu { color: #4ade80; font-weight: 600; margin-left: 12px; min-width: 40px; text-align: right; }
  .refresh {
    font-size: 11px;
    color: #444;
    text-align: right;
    margin-top: 16px;
  }
</style>
</head>
<body>
<h1>System Info</h1>
<div class="grid" id="grid"></div>
<div id="proc-card" class="card"></div>
<div class="refresh" id="ts"></div>

<script>
function barClass(pct) {
  return pct > 85 ? "danger" : pct > 60 ? "warn" : "";
}

function card(title, value, sub, pct) {
  return `<div class="card">
    <div class="card-title">${title}</div>
    <div class="card-value">${value}</div>
    <div class="card-sub">${sub}</div>
    <div class="bar-wrap"><div class="bar ${barClass(pct)}" style="width:${pct}%"></div></div>
  </div>`;
}

async function load() {
  let d;
  try {
    d = await fetch("/api").then(r => r.json());
  } catch(e) {
    return;
  }

  // CPU
  const cpuM = (d.cpu || "").match(/([\d.]+)% idle/);
  const cpuPct = cpuM ? Math.round(100 - parseFloat(cpuM[1])) : 0;
  const cpuSub = (d.cpu || "").replace("CPU usage:", "").trim();

  // Memory
  const mem = d.memory || {};
  const memSub = `${mem.used || 0} MB used / ${mem.total || 0} MB total &nbsp;·&nbsp; Free: ${mem.free || 0} MB`;

  // Battery
  const bat = d.battery || "";
  const batM = bat.match(/(\d+)%/);
  const batPct = batM ? parseInt(batM[1]) : 0;
  const charging = bat.includes("charging") && !bat.includes("discharging");
  const remainM = bat.match(/(\d+:\d+) remaining/);
  const batSub = (charging ? "⚡ Charging" : "🔋 Discharging") +
                 (remainM ? " &nbsp;·&nbsp; " + remainM[1] + " left" : "");

  // Disk
  const disk = d.disk || {};
  const diskPct = parseInt(disk.pct) || 0;
  const diskSub = `${disk.used || ""} used / ${disk.total || ""} total &nbsp;·&nbsp; Free: ${disk.free || ""}`;

  document.getElementById("grid").innerHTML =
    card("CPU",     cpuPct + "%",    cpuSub,  cpuPct) +
    card("Memory",  mem.pct + "%",   memSub,  mem.pct || 0) +
    card("Battery", batPct + "%",    batSub,  batPct) +
    card("Disk",    disk.pct || "0", diskSub, diskPct);

  document.getElementById("proc-card").innerHTML =
    `<div class="card-title">Top Processes</div>` +
    (d.processes || []).map(p =>
      `<div class="proc-row">
        <span class="proc-name">${p.name}</span>
        <span class="proc-cpu">${p.cpu.toFixed(1)}%</span>
      </div>`
    ).join("");

  document.getElementById("ts").textContent = "Updated: " + new Date().toLocaleTimeString();
}

load();
setInterval(load, 3000);
</script>
</body>
</html>"""

# ── 메인 ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    server = HTTPServer(("127.0.0.1", PORT), Handler)
    print(f"대시보드 서버 — http://127.0.0.1:{PORT}")
    server.serve_forever()
