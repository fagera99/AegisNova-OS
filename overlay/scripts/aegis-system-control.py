#!/usr/bin/env python3
"""
AegisNova OS — System Control API
===================================
Lightweight HTTP API server (root-level) that the JARVIS UI calls
via fetch() to execute real system commands.

Endpoints:
  POST /cmd    { "text": "open terminal" }  → natural language → shell action
  POST /exec   { "cmd": "nmap -sV ..." }    → direct shell execution (full-control mode)
  GET  /status                              → CPU, MEM, disk, network JSON
  POST /power  { "action": "shutdown" }     → shutdown/reboot/suspend

Runs on: http://localhost:9091
"""

import os, sys, json, subprocess, shlex, time, threading, re
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

PORT = 9091
FULL_CONTROL = False       # Unlocked when user explicitly requests
LOG_FILE = "/var/log/aegisnova/system-control.log"

os.makedirs("/var/log/aegisnova", exist_ok=True)

def log(msg):
    ts = datetime.utcnow().isoformat()
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass

def run_bg(cmd: str) -> dict:
    """Run a shell command in background, return immediately."""
    try:
        subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
        return {"ok": True, "output": f"Started: {cmd[:80]}"}
    except Exception as e:
        return {"ok": False, "output": str(e)}

def run_sync(cmd: str, timeout=10) -> dict:
    """Run a shell command synchronously, return output."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True,
                           text=True, timeout=timeout)
        return {"ok": r.returncode == 0,
                "output": (r.stdout + r.stderr).strip()[:2000]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "output": "Command timed out."}
    except Exception as e:
        return {"ok": False, "output": str(e)}

def get_status() -> dict:
    """Collect real-time system metrics."""
    cpu   = run_sync("top -bn1 | grep 'Cpu(s)' | awk '{print $2}'", 5)
    mem   = run_sync("free -m | awk '/^Mem/{printf \"%d/%d MB (%.0f%%)\", $3,$2,$3/$2*100}'", 5)
    disk  = run_sync("df -h / | awk 'NR==2{print $3\"/\"$2\" (\"$5\")\"}'", 5)
    net   = run_sync("cat /proc/net/dev | awk 'NR>2{rx+=$2;tx+=$10} END{printf \"↓%.1f MB  ↑%.1f MB\",rx/1048576,tx/1048576}'", 5)
    procs = run_sync("ps aux --no-headers | wc -l", 5)
    threat = run_sync("tail -5 /var/log/aegisnova/ai/safety.log 2>/dev/null | grep -c CRITICAL || echo 0", 5)
    return {
        "cpu":     cpu["output"] or "N/A",
        "mem":     mem["output"] or "N/A",
        "disk":    disk["output"] or "N/A",
        "net":     net["output"] or "N/A",
        "procs":   procs["output"].strip() or "N/A",
        "threat":  threat["output"].strip() or "0",
        "time":    datetime.now().strftime("%H:%M:%S"),
        "uptime":  run_sync("uptime -p", 3)["output"],
        "full_control": FULL_CONTROL,
    }

# ── Natural Language Command Router ──────────────────────────────────────────
COMMANDS = {
    # Applications
    "open terminal":       lambda: run_bg("DISPLAY=:0 gnome-terminal"),
    "open browser":        lambda: run_bg("DISPLAY=:0 chromium --new-window"),
    "open firefox":        lambda: run_bg("DISPLAY=:0 firefox"),
    "open files":          lambda: run_bg("DISPLAY=:0 nautilus"),
    "open editor":         lambda: run_bg("DISPLAY=:0 gedit"),
    "open wireshark":      lambda: run_bg("DISPLAY=:0 wireshark"),
    "open burpsuite":      lambda: run_bg("DISPLAY=:0 burpsuite"),
    "open metasploit":     lambda: run_bg("DISPLAY=:0 gnome-terminal -- msfconsole"),
    "run metasploit":      lambda: run_bg("DISPLAY=:0 gnome-terminal -- msfconsole"),
    "open htop":           lambda: run_bg("DISPLAY=:0 gnome-terminal -- htop"),
    "show processes":      lambda: run_bg("DISPLAY=:0 gnome-terminal -- htop"),

    # System control
    "screenshot":          lambda: run_bg("DISPLAY=:0 gnome-screenshot -f /tmp/aegis-$(date +%s).png"),
    "take screenshot":     lambda: run_bg("DISPLAY=:0 gnome-screenshot -f /tmp/aegis-$(date +%s).png"),
    "lock screen":         lambda: run_bg("DISPLAY=:0 loginctl lock-session"),
    "wipe memory":         lambda: run_bg("sudo /usr/local/bin/aegisnova-wipe.sh --memory"),
    "clean system":        lambda: run_bg("sudo /usr/local/bin/aegisnova-wipe.sh --all"),
    "update system":       lambda: run_bg("sudo /usr/local/bin/aegisnova-update.sh"),

    # Power
    "shutdown":            lambda: run_sync("shutdown -h now"),
    "reboot":              lambda: run_sync("reboot"),
    "suspend":             lambda: run_sync("systemctl suspend"),

    # Network
    "show firewall":       lambda: run_sync("nft list ruleset 2>/dev/null | head -30"),
    "enable firewall":     lambda: run_sync("systemctl restart nftables"),
    "disable firewall":    lambda: run_sync("systemctl stop nftables"),
    "show network":        lambda: run_sync("ip a && ip route"),
    "monitor traffic":     lambda: run_bg("DISPLAY=:0 gnome-terminal -- sudo tcpdump -i any -n"),

    # Security
    "check logs":          lambda: run_sync("tail -20 /var/log/syslog 2>/dev/null || journalctl -n 20"),
    "check threats":       lambda: run_sync("tail -20 /var/log/aegisnova/ai/safety.log 2>/dev/null"),
    "harden system":       lambda: run_bg("sudo /usr/local/bin/harden-system.sh"),
    "security check":      lambda: run_sync("lynis audit system --quick --no-colors 2>/dev/null | grep -E 'Warn|Sugg' | head -10"),
    "malware scan":        lambda: run_sync("clamscan -r /tmp 2>/dev/null | tail -5"),
    "check auditd":        lambda: run_sync("ausearch -ts today --just-one 2>/dev/null || journalctl -u auditd -n 10"),

    # AI agents
    "show agents":         lambda: run_sync("python3 /usr/local/bin/aegisnova-brain.py --status 2>/dev/null | head -20"),
    "brain status":        lambda: run_sync("systemctl is-active aegis-brain 2>/dev/null; systemctl status aegis-brain --no-pager -l 2>/dev/null | head -15"),
    "defend system":       lambda: run_bg("python3 /usr/local/bin/aegisnova-brain.py --defensive"),
    "spawn blue team":     lambda: run_bg("python3 /usr/local/bin/aegisnova-brain.py --swarm-defense"),
    "spawn red team":      lambda: run_bg("python3 /usr/local/bin/aegisnova-brain.py --offensive --target 127.0.0.1"),
    "full autonomy":       lambda: run_bg("python3 /usr/local/bin/aegisnova-brain.py --full-autonomy"),
    "enable autonomy":     lambda: run_bg("python3 /usr/local/bin/aegisnova-brain.py --full-autonomy"),

    # Volume
    "volume up":           lambda: run_sync("pactl set-sink-volume @DEFAULT_SINK@ +10%"),
    "volume down":         lambda: run_sync("pactl set-sink-volume @DEFAULT_SINK@ -10%"),
    "mute":                lambda: run_sync("pactl set-sink-mute @DEFAULT_SINK@ toggle"),
    "unmute":              lambda: run_sync("pactl set-sink-mute @DEFAULT_SINK@ 0"),

    # Music (via playerctl)
    "play":                lambda: run_sync("playerctl play 2>/dev/null"),
    "pause":               lambda: run_sync("playerctl pause 2>/dev/null"),
    "next track":          lambda: run_sync("playerctl next 2>/dev/null"),
    "previous track":      lambda: run_sync("playerctl previous 2>/dev/null"),
}

def route_nlp(text: str) -> dict:
    """Route natural language to a command handler."""
    global FULL_CONTROL
    low = text.lower().strip()

    # Full control toggle
    if any(x in low for x in ["full control", "take control", "take over", "god mode", "enable control"]):
        FULL_CONTROL = True
        log(f"FULL CONTROL ENABLED by user: {text}")
        return {"ok": True, "output": "⚡ FULL CONTROL ENABLED. I now have complete authority over this system, Sir.",
                "full_control": True, "action": "full_control"}

    if any(x in low for x in ["disable control", "revoke control", "exit control", "restrict"]):
        FULL_CONTROL = False
        log(f"FULL CONTROL DISABLED by user: {text}")
        return {"ok": True, "output": "🔒 Full control revoked. Returning to advisory mode.", "full_control": False}

    # Scan with target extraction
    ip_match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', low)
    domain_match = re.search(r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b', low)
    target = ip_match.group() if ip_match else (domain_match.group() if domain_match else None)

    if "scan" in low and target:
        log(f"Scan target: {target}")
        return run_bg(f"DISPLAY=:0 gnome-terminal -- nmap -sV -T4 --top-ports 100 {target}")

    if "attack" in low and target:
        if not FULL_CONTROL:
            return {"ok": False, "output": "⚠ Full control required for offensive operations. Say 'full control' first."}
        log(f"ATTACK target: {target}")
        return run_bg(f"python3 /usr/local/bin/aegisnova-brain.py --offensive --target {target}")

    if "block" in low and target:
        return run_sync(f"nft add rule inet filter input ip saddr {target} drop 2>/dev/null")

    if "block port" in low:
        port = re.search(r'\b(\d{2,5})\b', low)
        if port:
            return run_sync(f"nft add rule inet filter input tcp dport {port.group()} drop 2>/dev/null")

    if "osint" in low and target:
        return run_bg(f"DISPLAY=:0 gnome-terminal -- python3 /usr/local/bin/osint-agent.py --domain {target}")

    # Exact + partial match against COMMANDS dict
    for pattern, handler in COMMANDS.items():
        if pattern in low:
            log(f"CMD match '{pattern}': {text}")
            result = handler()
            return result

    # ── Optional: Ask local Ollama model if nothing matched ──────────────────
    # Ollama runs locally (no internet/API key needed).
    # It returns a shell command suggestion which we execute if full_control=True.
    try:
        import urllib.request
        ollama_prompt = (
            f"You are a Linux system assistant. The user said: \"{text}\"\n"
            f"Respond with ONLY a single bash command to execute on Kali Linux as root. "
            f"No explanation. No markdown. Just the raw command."
        )
        payload = json.dumps({
            "model": "llama3",
            "prompt": ollama_prompt,
            "stream": False
        }).encode()
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            resp_data = json.loads(resp.read())
            ai_cmd = resp_data.get("response", "").strip().strip("`").strip()
            if ai_cmd and len(ai_cmd) < 300:
                log(f"Ollama suggested: {ai_cmd}")
                if FULL_CONTROL:
                    result = run_sync(ai_cmd, timeout=15)
                    result["ai_suggested"] = ai_cmd
                    return result
                else:
                    return {
                        "ok": True,
                        "output": f"🤖 AI suggests: `{ai_cmd}`\nSay 'full control' to let me execute it, Sir.",
                        "ai_suggested": ai_cmd
                    }
    except Exception as ollama_err:
        log(f"Ollama not available: {ollama_err}")
        # Ollama offline — graceful fallback, no crash

    # Final fallback
    return {"ok": True, "output": "Command acknowledged. Standing by.", "action": "brain"}


# ── HTTP Handler ──────────────────────────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # Suppress default HTTP logs

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path == "/status":
            self._json(200, get_status())
        elif self.path == "/ping":
            self._json(200, {"ok": True, "full_control": FULL_CONTROL})
        else:
            self._json(404, {"error": "Not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body) if body else {}
        except Exception:
            data = {}

        if self.path == "/cmd":
            text = data.get("text", "").strip()
            if not text:
                return self._json(400, {"error": "No text provided"})
            log(f"NLP CMD: {text}")
            result = route_nlp(text)
            self._json(200, result)

        elif self.path == "/exec":
            if not FULL_CONTROL:
                return self._json(403, {"error": "Full control not enabled. Say 'full control' first."})
            cmd = data.get("cmd", "").strip()
            if not cmd:
                return self._json(400, {"error": "No cmd provided"})
            mode = data.get("mode", "sync")
            log(f"EXEC [{mode}]: {cmd}")
            result = run_bg(cmd) if mode == "bg" else run_sync(cmd)
            self._json(200, result)

        elif self.path == "/power":
            action = data.get("action", "")
            if action == "shutdown":
                self._json(200, {"ok": True, "output": "Shutting down..."})
                threading.Timer(1.0, lambda: os.system("shutdown -h now")).start()
            elif action == "reboot":
                self._json(200, {"ok": True, "output": "Rebooting..."})
                threading.Timer(1.0, lambda: os.system("reboot")).start()
            elif action == "suspend":
                self._json(200, run_sync("systemctl suspend"))
            else:
                self._json(400, {"error": f"Unknown power action: {action}"})
        else:
            self._json(404, {"error": "Not found"})


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log("=" * 60)
    log("  AegisNova System Control API")
    log(f"  Listening on http://0.0.0.0:{PORT}")
    log("  Full control: DISABLED (user must request)")
    log("=" * 60)
    try:
        srv = HTTPServer(("0.0.0.0", PORT), Handler)
        srv.serve_forever()
    except KeyboardInterrupt:
        log("Shutting down System Control API.")
