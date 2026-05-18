#!/usr/bin/env python3
"""
AegisNova OS — eBPF Kernel Telemetry Sensor
=============================================
Streams kernel events via eBPF/bpftrace, classifies them with an LLM
(via LangChain), and writes alerts to systemd-journal + optional webhook.

Requires: bpfcc-tools, python3-bcc, langchain, requests
Run as:   systemctl start ebpf-sensor   (or directly as root)
"""

import json
import os
import sys
import time
import signal
import subprocess
import logging
from datetime import datetime
from typing import Optional

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------
LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "http://127.0.0.1:8080/completion")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
ALERT_THRESHOLD = os.getenv("ALERT_THRESHOLD", "medium")  # low, medium, high
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "5"))

# Setup logging to systemd journal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("ebpf-sensor")

# ---------------------------------------------------------------------------
# eBPF probes (bpftrace one-liners)
# ---------------------------------------------------------------------------
EBPF_PROBES = {
    "execsnoop": {
        "cmd": ["bpftrace", "-e",
                'tracepoint:syscalls:sys_enter_execve '
                '{ printf("EXEC pid=%d comm=%s args=%s\\n", '
                'pid, comm, str(args->filename)); }'],
        "desc": "Track process executions",
    },
    "opensnoop": {
        "cmd": ["bpftrace", "-e",
                'tracepoint:syscalls:sys_enter_openat '
                '{ printf("OPEN pid=%d comm=%s file=%s\\n", '
                'pid, comm, str(args->filename)); }'],
        "desc": "Track file opens",
    },
    "tcpconnect": {
        "cmd": ["bpftrace", "-e",
                'kprobe:tcp_connect '
                '{ printf("TCP_CONN pid=%d comm=%s\\n", pid, comm); }'],
        "desc": "Track outbound TCP connections",
    },
}

# ---------------------------------------------------------------------------
# LLM classification via simple HTTP (no LangChain dependency at minimum)
# ---------------------------------------------------------------------------
def classify_event(event_text: str) -> dict:
    """Send kernel event to local LLM for threat classification."""
    prompt = f"""You are a kernel security analyst. Classify this Linux kernel event.
Respond ONLY with valid JSON: {{"severity": "low|medium|high|critical", "category": "string", "summary": "string"}}

Event: {event_text}"""

    try:
        import requests
        resp = requests.post(
            LLM_ENDPOINT,
            json={"prompt": prompt, "n_predict": 200, "temperature": 0.1},
            timeout=10,
        )
        if resp.status_code == 200:
            content = resp.json().get("content", "{}")
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
    except Exception as e:
        log.debug(f"LLM classification failed: {e}")

    # Fallback classification
    return {"severity": "low", "category": "unknown", "summary": event_text[:100]}


def send_webhook(alert: dict) -> None:
    """Forward alert to webhook endpoint if configured."""
    if not WEBHOOK_URL:
        return
    try:
        import requests
        requests.post(WEBHOOK_URL, json=alert, timeout=5)
    except Exception as e:
        log.warning(f"Webhook send failed: {e}")


def should_alert(severity: str) -> bool:
    """Check if severity meets the configured threshold."""
    levels = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    return levels.get(severity, 0) >= levels.get(ALERT_THRESHOLD, 1)


# ---------------------------------------------------------------------------
# LangChain tool-use agent (used when langchain is available)
# ---------------------------------------------------------------------------
def create_langchain_agent():
    """Create a LangChain agent with security analysis tools."""
    try:
        from langchain.agents import initialize_agent, AgentType
        from langchain.tools import Tool
        from langchain_community.llms import OpenAI

        tools = [
            Tool(
                name="ClassifyEvent",
                func=lambda e: json.dumps(classify_event(e)),
                description="Classify a kernel security event",
            ),
            Tool(
                name="SendAlert",
                func=lambda a: send_webhook(json.loads(a)),
                description="Send alert to webhook",
            ),
            Tool(
                name="QueryAuditLog",
                func=lambda q: subprocess.getoutput(f"ausearch -m {q} --just-one"),
                description="Query auditd logs",
            ),
        ]

        llm = OpenAI(
            base_url=LLM_ENDPOINT.replace("/completion", "/v1"),
            api_key="not-needed",
            temperature=0.1,
        )

        return initialize_agent(
            tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True
        )
    except ImportError:
        log.info("LangChain not available — using direct LLM classification.")
        return None


# ---------------------------------------------------------------------------
# Main event loop
# ---------------------------------------------------------------------------
class EBPFSensor:
    def __init__(self):
        self.running = True
        self.processes = {}
        self.agent = create_langchain_agent()
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)

    def _shutdown(self, signum, frame):
        log.info("Shutting down eBPF sensor …")
        self.running = False
        for name, proc in self.processes.items():
            proc.terminate()

    def start_probes(self):
        """Launch all eBPF probe subprocesses."""
        for name, probe in EBPF_PROBES.items():
            try:
                proc = subprocess.Popen(
                    probe["cmd"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    bufsize=1,
                )
                self.processes[name] = proc
                log.info(f"Started probe: {name} — {probe['desc']}")
            except FileNotFoundError:
                log.warning(f"bpftrace not found — probe {name} skipped.")
            except Exception as e:
                log.error(f"Failed to start probe {name}: {e}")

    def process_events(self):
        """Read and classify events from all probes (select-based, non-busy)."""
        import select

        while self.running:
            if not self.processes:
                time.sleep(5)
                continue

            # Build list of readable file descriptors
            fds = {proc.stdout: name for name, proc in list(self.processes.items())
                   if proc.stdout and proc.poll() is None}

            if not fds:
                time.sleep(1)
                continue

            try:
                readable, _, _ = select.select(list(fds.keys()), [], [], 1.0)
            except ValueError:
                time.sleep(0.5)
                continue

            for fd in readable:
                name = fds.get(fd, "unknown")
                try:
                    line = fd.readline()
                    if not line:
                        continue
                    line = line.strip()
                    if not line:
                        continue

                    # Classify with LLM
                    classification = classify_event(line)
                    severity = classification.get("severity", "low")

                    if should_alert(severity):
                        alert = {
                            "timestamp": datetime.utcnow().isoformat(),
                            "probe": name,
                            "raw_event": line,
                            "classification": classification,
                        }
                        log.warning(
                            f"🚨 [{severity.upper()}] {classification.get('summary', line)}"
                        )
                        send_webhook(alert)
                    else:
                        log.debug(f"[{severity}] {line[:80]}")

                except Exception as e:
                    log.error(f"Error processing {name}: {e}")

            # Clean up dead probes
            for name, proc in list(self.processes.items()):
                if proc.poll() is not None:
                    log.warning(f"Probe {name} exited (rc={proc.returncode}). Restarting …")
                    del self.processes[name]
                    # Auto-restart the probe
                    try:
                        probe = EBPF_PROBES.get(name, {})
                        if probe:
                            new_proc = __import__('subprocess').Popen(
                                probe["cmd"], stdout=__import__('subprocess').PIPE,
                                stderr=__import__('subprocess').DEVNULL,
                                text=True, bufsize=1,
                            )
                            self.processes[name] = new_proc
                            log.info(f"Probe {name} restarted.")
                    except Exception as restart_err:
                        log.error(f"Failed to restart probe {name}: {restart_err}")

    def run(self):
        log.info("═" * 60)
        log.info("  AegisNova eBPF Kernel Telemetry Sensor")
        log.info(f"  LLM Endpoint : {LLM_ENDPOINT}")
        log.info(f"  Alert Level  : {ALERT_THRESHOLD}")
        log.info(f"  Webhook      : {WEBHOOK_URL or 'disabled'}")
        log.info("═" * 60)

        self.start_probes()

        if not self.processes:
            log.error("No probes started. Is bpftrace installed? Are we root?")
            sys.exit(1)

        self.process_events()
        log.info("eBPF sensor stopped.")


if __name__ == "__main__":
    sensor = EBPFSensor()
    sensor.run()
