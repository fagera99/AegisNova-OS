#!/usr/bin/env python3
"""
AegisNova OS — AEGIS ASSISTANT (JARVIS-Style AI Companion)
==========================================================
A visual and voice-enabled AI assistant that controls the OS.

Features:
- 🌊 Animated wave/light UI in browser
- 🎤 Voice commands ("Open terminal", "Scan target", "Defend system")
- 🔊 Voice responses with synthesized speech
- 🧠 Natural language command parsing
- 🎨 Visual feedback (desktop notifications, wave animations)
- 🤖 Integration with Aegis Brain for autonomous operations

Usage:
    python3 aegisnova-assistant.py --web
    python3 aegisnova-assistant.py --voice
    python3 aegisnova-assistant.py --full
"""

import os
import argparse
import sys
import json
import time
import queue
import random
import asyncio
import threading
import subprocess
import webbrowser
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

# Web server
from http.server import HTTPServer, BaseHTTPRequestHandler
import socketserver

# Voice imports (with fallbacks + auto-install)
STT_AVAILABLE = False
TTS_AVAILABLE = False

try:
    import speech_recognition as sr
    STT_AVAILABLE = True
except ImportError:
    print("[ASSISTANT] speech_recognition missing — attempting auto-install ...")
    os.system("pip3 install --break-system-packages SpeechRecognition 2>/dev/null || pip3 install SpeechRecognition")
    try:
        import speech_recognition as sr
        STT_AVAILABLE = True
    except ImportError:
        STT_AVAILABLE = False

try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    print("[ASSISTANT] pyttsx3 missing — attempting auto-install ...")
    os.system("pip3 install --break-system-packages pyttsx3 2>/dev/null || pip3 install pyttsx3")
    try:
        import pyttsx3
        TTS_AVAILABLE = True
    except ImportError:
        TTS_AVAILABLE = False

# ── Configuration ──
ASSISTANT_DIR = "/opt/aegisnova/assistant"
UI_DIR = f"{ASSISTANT_DIR}/ui"
VOICE_DIR = f"{ASSISTANT_DIR}/voice"
STATE_FILE = f"{ASSISTANT_DIR}/state.json"

try:
    os.makedirs(ASSISTANT_DIR, exist_ok=True)
    os.makedirs(UI_DIR, exist_ok=True)
    os.makedirs(VOICE_DIR, exist_ok=True)
except PermissionError:
    # Fallback to user home if not root
    ASSISTANT_DIR = os.path.expanduser("~/.aegisnova/assistant")
    UI_DIR = f"{ASSISTANT_DIR}/ui"
    VOICE_DIR = f"{ASSISTANT_DIR}/voice"
    STATE_FILE = f"{ASSISTANT_DIR}/state.json"
    os.makedirs(ASSISTANT_DIR, exist_ok=True)
    os.makedirs(UI_DIR, exist_ok=True)
    os.makedirs(VOICE_DIR, exist_ok=True)

WAKE_WORDS = ["hey aegis", "ok aegis", "aegis nova", "hello aegis"]
SLEEP_WORDS = ["sleep", "go away", "shutdown", "goodbye", "stop listening"]


class AssistantState(Enum):
    IDLE = "idle"           # Waiting for wake word
    LISTENING = "listening" # Actively listening for command
    THINKING = "thinking"   # Processing command
    SPEAKING = "speaking"   # Giving voice response
    EXECUTING = "executing" # Running command
    ERROR = "error"         # Something went wrong


class CommandType(Enum):
    SYSTEM = "system"       # OS-level commands
    SECURITY = "security"   # Security operations
    OFFENSIVE = "offensive" # Red team commands
    DEFENSIVE = "defensive" # Blue team commands
    BRAIN = "brain"         # Brain orchestration
    INFO = "info"           # Information queries
    FUN = "fun"             # Easter eggs
    UNKNOWN = "unknown"


@dataclass
class Command:
    raw_text: str
    command_type: CommandType
    action: str
    parameters: Dict[str, Any]
    confidence: float


class VoiceEngine:
    """Speech-to-Text and Text-to-Speech engine."""
    
    def __init__(self):
        self.recognizer = None
        self.microphone = None
        self.tts_engine = None
        self.is_listening = False
        
        if STT_AVAILABLE:
            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()
            # Calibrate for ambient noise
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
            print("[ASSISTANT] 🎤 Voice engine initialized")
        
        if TTS_AVAILABLE:
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty('rate', 175)
            self.tts_engine.setProperty('volume', 0.9)
            # Try to use a male voice (Jarvis-like)
            voices = self.tts_engine.getProperty('voices')
            for voice in voices:
                if 'male' in voice.name.lower() or 'david' in voice.name.lower():
                    self.tts_engine.setProperty('voice', voice.id)
                    break
            print("[ASSISTANT] 🔊 TTS engine initialized")
    
    def listen(self, timeout: int = 5) -> Optional[str]:
        """Listen for voice input and convert to text."""
        if not STT_AVAILABLE:
            return None
        
        with self.microphone as source:
            print("[ASSISTANT] 🎤 Listening...")
            try:
                audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=5)
                text = self.recognizer.recognize_google(audio)
                print(f"[ASSISTANT] Heard: \"{text}\"")
                return text
            except sr.WaitTimeoutError:
                return None
            except sr.UnknownValueError:
                return None
            except sr.RequestError as e:
                print(f"[ASSISTANT] Speech recognition error: {e}")
                return None
    
    def speak(self, text: str):
        """Speak text using TTS."""
        print(f"[ASSISTANT] 🔊 Speaking: {text}")
        
        if TTS_AVAILABLE and self.tts_engine:
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        else:
            # Fallback to system TTS
            try:
                subprocess.run(["espeak", text], timeout=10, capture_output=True)
            except:
                pass


class CommandParser:
    """Parse natural language into executable commands."""
    
    def __init__(self):
        self.patterns = self._load_patterns()
    
    def _load_patterns(self) -> Dict:
        return {
            CommandType.SYSTEM: {
                # Applications
                "open terminal": {"action": "open_terminal", "params": {}},
                "open browser": {"action": "open_browser", "params": {}},
                "open file manager": {"action": "open_filemanager", "params": {}},
                "open text editor": {"action": "open_editor", "params": {}},
                "show desktop": {"action": "show_desktop", "params": {}},
                "take screenshot": {"action": "screenshot", "params": {}},
                "lock screen": {"action": "lock_screen", "params": {}},
                # System control
                "shutdown": {"action": "shutdown", "params": {}},
                "reboot": {"action": "reboot", "params": {}},
                "sleep": {"action": "sleep_system", "params": {}},
                "show system info": {"action": "system_info", "params": {}},
                "show cpu usage": {"action": "cpu_usage", "params": {}},
                "show memory": {"action": "memory_usage", "params": {}},
                "show disk": {"action": "disk_usage", "params": {}},
                "show network": {"action": "network_info", "params": {}},
                "show processes": {"action": "show_processes", "params": {}},
                "show users": {"action": "show_users", "params": {}},
                "update system": {"action": "update_system", "params": {}},
                "clean system": {"action": "clean_system", "params": {}},
                "wipe memory": {"action": "wipe_memory", "params": {}},
                # Services
                "show services": {"action": "show_services", "params": {}},
                "restart service": {"action": "restart_service", "params": {}},
                "start docker": {"action": "start_docker", "params": {}},
                "stop docker": {"action": "stop_docker", "params": {}},
                # Files
                "find file": {"action": "find_file", "params": {}},
                "show files": {"action": "show_files", "params": {}},
                "create folder": {"action": "create_folder", "params": {}},
            },
            CommandType.SECURITY: {
                # Scanning
                "scan network": {"action": "scan_network", "params": {"target": "127.0.0.1"}},
                "scan target": {"action": "scan_target", "params": {}},
                "quick scan": {"action": "quick_scan", "params": {}},
                "deep scan": {"action": "deep_scan", "params": {}},
                "scan ports": {"action": "scan_ports", "params": {}},
                "run vulnerability scan": {"action": "vuln_scan", "params": {}},
                "check security": {"action": "security_check", "params": {}},
                "harden system": {"action": "harden_system", "params": {}},
                # Firewall
                "show firewall": {"action": "show_firewall", "params": {}},
                "enable firewall": {"action": "enable_firewall", "params": {}},
                "disable firewall": {"action": "disable_firewall", "params": {}},
                "block port": {"action": "block_port", "params": {}},
                "allow port": {"action": "allow_port", "params": {}},
                # Monitoring
                "show logs": {"action": "show_logs", "params": {}},
                "check for threats": {"action": "threat_check", "params": {}},
                "monitor traffic": {"action": "monitor_traffic", "params": {}},
                "check audit": {"action": "check_audit", "params": {}},
                # Encryption
                "encrypt file": {"action": "encrypt_file", "params": {}},
                "decrypt file": {"action": "decrypt_file", "params": {}},
                "setup persistence": {"action": "setup_persistence", "params": {}},
                "setup yubikey": {"action": "setup_yubikey", "params": {}},
                "setup secure boot": {"action": "setup_secure_boot", "params": {}},
            },
            CommandType.OFFENSIVE: {
                "attack target": {"action": "attack_target", "params": {}},
                "run exploit": {"action": "run_exploit", "params": {}},
                "do reconnaissance": {"action": "recon_target", "params": {}},
                "scan ports": {"action": "scan_ports", "params": {}},
                "brute force": {"action": "bruteforce", "params": {}},
                "capture handshake": {"action": "capture_handshake", "params": {}},
                "run metasploit": {"action": "run_msf", "params": {}},
                "run sqlmap": {"action": "run_sqlmap", "params": {}},
                "run nmap": {"action": "run_nmap", "params": {}},
                "run burpsuite": {"action": "run_burp", "params": {}},
                "run wireshark": {"action": "run_wireshark", "params": {}},
                "spawn red team": {"action": "spawn_offensive", "params": {}},
                "launch offensive swarm": {"action": "offensive_swarm", "params": {}},
                "run osint": {"action": "run_osint", "params": {}},
            },
            CommandType.DEFENSIVE: {
                "defend system": {"action": "defend_system", "params": {}},
                "monitor network": {"action": "monitor_network", "params": {}},
                "analyze traffic": {"action": "analyze_traffic", "params": {}},
                "check for malware": {"action": "malware_check", "params": {}},
                "isolate host": {"action": "isolate_host", "params": {}},
                "block ip": {"action": "block_ip", "params": {}},
                "allow ip": {"action": "allow_ip", "params": {}},
                "spawn blue team": {"action": "spawn_defensive", "params": {}},
                "launch defensive swarm": {"action": "defensive_swarm", "params": {}},
                "run incident response": {"action": "incident_response", "params": {}},
                "run wazuh": {"action": "run_wazuh", "params": {}},
                "run suricata": {"action": "run_suricata", "params": {}},
                "run elk": {"action": "run_elk", "params": {}},
                "generate sigma rules": {"action": "generate_sigma", "params": {}},
            },
            CommandType.BRAIN: {
                "wake up brain": {"action": "brain_wake", "params": {}},
                "sleep brain": {"action": "brain_sleep", "params": {}},
                "show brain status": {"action": "brain_status", "params": {}},
                "enable autonomy": {"action": "enable_autonomy", "params": {}},
                "disable autonomy": {"action": "disable_autonomy", "params": {}},
                "spawn agent": {"action": "spawn_agent", "params": {}},
                "destroy agent": {"action": "destroy_agent", "params": {}},
                "show agents": {"action": "show_agents", "params": {}},
                "show codex": {"action": "show_codex", "params": {}},
                "full autonomy": {"action": "enable_autonomy", "params": {}},
            },
            CommandType.INFO: {
                "what time is it": {"action": "tell_time", "params": {}},
                "what date is it": {"action": "tell_date", "params": {}},
                "who are you": {"action": "introduce", "params": {}},
                "what can you do": {"action": "list_capabilities", "params": {}},
                "show weather": {"action": "weather", "params": {}},
                "help": {"action": "help", "params": {}},
                "show version": {"action": "show_version", "params": {}},
            },
            CommandType.FUN: {
                "hello": {"action": "greet", "params": {}},
                "how are you": {"action": "mood_check", "params": {}},
                "tell me a joke": {"action": "joke", "params": {}},
                "sing a song": {"action": "sing", "params": {}},
                "i am iron man": {"action": "iron_man", "params": {}},
                "jarvis": {"action": "jarvis_mode", "params": {}},
                "activate ultron": {"action": "ultron_mode", "params": {}},
                "i am batman": {"action": "batman_mode", "params": {}},
            },
        }
    
    def parse(self, text: str) -> Command:
        """Parse natural language text into a command."""
        text_lower = text.lower().strip()
        
        best_match = None
        best_type = CommandType.UNKNOWN
        best_confidence = 0.0
        
        for cmd_type, patterns in self.patterns.items():
            for pattern, action_data in patterns.items():
                # Exact match
                if pattern == text_lower:
                    return Command(
                        raw_text=text,
                        command_type=cmd_type,
                        action=action_data["action"],
                        parameters=action_data["params"],
                        confidence=1.0
                    )
                
                # Partial match
                if pattern in text_lower or text_lower in pattern:
                    confidence = len(set(text_lower.split()) & set(pattern.split())) / len(set(pattern.split()))
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = action_data
                        best_type = cmd_type
        
        if best_match and best_confidence > 0.3:
            return Command(
                raw_text=text,
                command_type=best_type,
                action=best_match["action"],
                parameters=best_match["params"],
                confidence=best_confidence
            )
        
        # Check for target extraction (IP, domain, etc.)
        import re
        ip_match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', text)
        domain_match = re.search(r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b', text)
        
        if "scan" in text_lower and ip_match:
            return Command(text, CommandType.SECURITY, "scan_target", {"target": ip_match.group()}, 0.7)
        if "attack" in text_lower and ip_match:
            return Command(text, CommandType.OFFENSIVE, "attack_target", {"target": ip_match.group()}, 0.7)
        if "attack" in text_lower and domain_match:
            return Command(text, CommandType.OFFENSIVE, "attack_target", {"target": domain_match.group()}, 0.7)
        
        return Command(text, CommandType.UNKNOWN, "unknown", {}, 0.0)


class ActionExecutor:
    """Execute parsed commands on the system."""
    
    def __init__(self, voice: VoiceEngine):
        self.voice = voice
    
    def execute(self, command: Command) -> Dict[str, Any]:
        """Execute a command and return results."""
        action = command.action
        params = command.parameters
        
        print(f"[ASSISTANT] Executing: {action} with params {params}")
        
        # Route to appropriate handler
        handlers = {
            # System
            "open_terminal": self._open_terminal,
            "open_browser": self._open_browser,
            "open_filemanager": self._open_filemanager,
            "open_editor": self._open_editor,
            "show_desktop": self._show_desktop,
            "screenshot": self._screenshot,
            "lock_screen": self._lock_screen,
            "shutdown": self._shutdown,
            "reboot": self._reboot,
            "sleep_system": self._sleep_system,
            "system_info": self._system_info,
            "cpu_usage": self._cpu_usage,
            "memory_usage": self._memory_usage,
            "disk_usage": self._disk_usage,
            "network_info": self._network_info,
            "show_processes": self._show_processes,
            "show_users": self._show_users,
            "show_services": self._show_services,
            "restart_service": self._restart_service,
            "start_docker": self._start_docker,
            "stop_docker": self._stop_docker,
            "update_system": self._update_system,
            "clean_system": self._clean_system,
            "wipe_memory": self._wipe_memory,
            "find_file": self._find_file,
            "show_files": self._show_files,
            "create_folder": self._create_folder,
            # Security
            "scan_network": self._scan_network,
            "scan_target": self._scan_target,
            "quick_scan": self._quick_scan,
            "deep_scan": self._deep_scan,
            "scan_ports": self._scan_ports,
            "vuln_scan": self._vuln_scan,
            "security_check": self._security_check,
            "harden_system": self._harden_system,
            "show_firewall": self._show_firewall,
            "enable_firewall": self._enable_firewall,
            "disable_firewall": self._disable_firewall,
            "block_port": self._block_port,
            "allow_port": self._allow_port,
            "show_logs": self._show_logs,
            "threat_check": self._threat_check,
            "monitor_traffic": self._monitor_traffic,
            "check_audit": self._check_audit,
            "encrypt_file": self._encrypt_file,
            "decrypt_file": self._decrypt_file,
            "setup_persistence": self._setup_persistence,
            "setup_yubikey": self._setup_yubikey,
            "setup_secure_boot": self._setup_secure_boot,
            # Offensive
            "attack_target": self._attack_target,
            "run_exploit": self._run_exploit,
            "recon_target": self._recon_target,
            "scan_ports": self._scan_ports,
            "bruteforce": self._bruteforce,
            "capture_handshake": self._capture_handshake,
            "run_msf": self._run_msf,
            "run_sqlmap": self._run_sqlmap,
            "run_nmap": self._run_nmap,
            "run_burp": self._run_burp,
            "run_wireshark": self._run_wireshark,
            "spawn_offensive": self._spawn_offensive,
            "offensive_swarm": self._offensive_swarm,
            "run_osint": self._run_osint,
            # Defensive
            "defend_system": self._defend_system,
            "monitor_network": self._monitor_network,
            "analyze_traffic": self._analyze_traffic,
            "malware_check": self._malware_check,
            "isolate_host": self._isolate_host,
            "block_ip": self._block_ip,
            "allow_ip": self._allow_ip,
            "spawn_defensive": self._spawn_defensive,
            "defensive_swarm": self._defensive_swarm,
            "incident_response": self._incident_response,
            "run_wazuh": self._run_wazuh,
            "run_suricata": self._run_suricata,
            "run_elk": self._run_elk,
            "generate_sigma": self._generate_sigma,
            # Brain
            "brain_wake": self._brain_wake,
            "brain_sleep": self._brain_sleep,
            "brain_status": self._brain_status,
            "enable_autonomy": self._enable_autonomy,
            "disable_autonomy": self._disable_autonomy,
            "spawn_agent": self._spawn_agent,
            "destroy_agent": self._destroy_agent,
            "show_agents": self._show_agents,
            "show_codex": self._show_codex,
            # Info
            "tell_time": self._tell_time,
            "tell_date": self._tell_date,
            "introduce": self._introduce,
            "list_capabilities": self._list_capabilities,
            "weather": self._weather,
            "help": self._help_assistant,
            "show_version": self._show_version,
            # Fun
            "greet": self._greet,
            "mood_check": self._mood_check,
            "joke": self._joke,
            "sing": self._sing,
            "iron_man": self._iron_man,
            "jarvis_mode": self._jarvis_mode,
            "ultron_mode": self._ultron_mode,
            "batman_mode": self._batman_mode,
        }
        
        handler = handlers.get(action, self._unknown_command)
        return handler(params)
    
    def _run_shell(self, cmd: str, timeout: int = 30) -> str:
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
            return result.stdout.strip()[:500]
        except Exception as e:
            return f"Error: {str(e)}"
    
    # System Handlers
    def _open_terminal(self, p): 
        subprocess.Popen(["gnome-terminal"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"success": True, "response": "Terminal opened."}
    
    def _open_browser(self, p):
        subprocess.Popen(["firefox"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"success": True, "response": "Browser opened."}
    
    def _show_desktop(self, p):
        self._run_shell("wmctrl -k on")
        return {"success": True, "response": "Desktop shown."}
    
    def _screenshot(self, p):
        filename = f"/tmp/screenshot-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
        self._run_shell(f"gnome-screenshot -f {filename}")
        return {"success": True, "response": f"Screenshot saved to {filename}"}
    
    def _system_info(self, p):
        info = self._run_shell("uname -a && uptime")
        return {"success": True, "response": f"System: {info}"}
    
    def _cpu_usage(self, p):
        cpu = self._run_shell("top -bn1 | grep 'Cpu(s)' | awk '{print $2}' | cut -d'%' -f1")
        return {"success": True, "response": f"CPU usage: {cpu}%"}
    
    def _memory_usage(self, p):
        mem = self._run_shell("free -h | grep Mem")
        return {"success": True, "response": f"Memory: {mem}"}
    
    def _update_system(self, p):
        subprocess.Popen(["sudo", "/usr/local/bin/aegisnova-update.sh"], stdout=subprocess.DEVNULL)
        return {"success": True, "response": "System update started in background."}
    
    def _clean_system(self, p):
        subprocess.Popen(["sudo", "/usr/local/bin/aegisnova-wipe.sh", "--all"], stdout=subprocess.DEVNULL)
        return {"success": True, "response": "System cleanup started."}
    
    # Security Handlers
    def _scan_target(self, p):
        target = p.get("target", "127.0.0.1")
        subprocess.Popen(["nmap", "-sV", "-T4", "--top-ports", "50", target], stdout=subprocess.DEVNULL)
        return {"success": True, "response": f"Scanning {target}... Check terminal for results."}
    
    def _vuln_scan(self, p):
        subprocess.Popen(["sudo", "/usr/local/bin/aegisnova-vulnscan.sh", "--now"], stdout=subprocess.DEVNULL)
        return {"success": True, "response": "Vulnerability scan started."}
    
    def _security_check(self, p):
        result = self._run_shell("lynis audit system --quick --no-colors 2>/dev/null | grep -E 'Warning|Suggestion' | head -5")
        return {"success": True, "response": f"Security check complete:\n{result}"}
    
    def _harden_system(self, p):
        subprocess.Popen(["sudo", "/usr/local/bin/harden-system.sh"], stdout=subprocess.DEVNULL)
        return {"success": True, "response": "System hardening applied."}
    
    def _show_firewall(self, p):
        rules = self._run_shell("nft list ruleset 2>/dev/null | head -20")
        return {"success": True, "response": f"Firewall rules:\n{rules}"}
    
    # Offensive Handlers
    def _spawn_offensive(self, p):
        subprocess.Popen(["python3", "/usr/local/bin/aegisnova-brain.py", "--offensive", "--target", "127.0.0.1"], stdout=subprocess.DEVNULL)
        return {"success": True, "response": "Offensive agent swarm deployed! VIPER and GHOST are moving."}
    
    def _offensive_swarm(self, p):
        subprocess.Popen(["python3", "/usr/local/bin/aegisnova-brain.py", "--swarm-offense", "--target", "127.0.0.1"], stdout=subprocess.DEVNULL)
        return {"success": True, "response": "Full offensive swarm activated! All agents engaging."}
    
    def _run_msf(self, p):
        subprocess.Popen(["gnome-terminal", "--", "msfconsole"], stdout=subprocess.DEVNULL)
        return {"success": True, "response": "Metasploit console opened."}
    
    # Defensive Handlers
    def _spawn_defensive(self, p):
        subprocess.Popen(["python3", "/usr/local/bin/aegisnova-brain.py", "--defensive"], stdout=subprocess.DEVNULL)
        return {"success": True, "response": "Defensive agents deployed! SENTINEL and OWL are watching."}
    
    def _defensive_swarm(self, p):
        subprocess.Popen(["python3", "/usr/local/bin/aegisnova-brain.py", "--swarm-defense"], stdout=subprocess.DEVNULL)
        return {"success": True, "response": "Full defensive swarm activated! Perimeter secured."}
    
    def _monitor_network(self, p):
        subprocess.Popen(["gnome-terminal", "--", "sudo", "iftop"], stdout=subprocess.DEVNULL)
        return {"success": True, "response": "Network monitor opened."}
    
    def _malware_check(self, p):
        result = self._run_shell("clamscan -r /tmp 2>/dev/null | tail -5")
        return {"success": True, "response": f"Malware scan:\n{result}"}
    
    # Brain Handlers
    def _brain_status(self, p):
        result = self._run_shell("python3 /usr/local/bin/aegisnova-brain.py --status 2>/dev/null | head -10")
        return {"success": True, "response": f"Brain status:\n{result}"}
    
    def _enable_autonomy(self, p):
        subprocess.Popen(["python3", "/usr/local/bin/aegisnova-brain.py", "--full-autonomy"], stdout=subprocess.DEVNULL)
        return {"success": True, "response": "Full autonomy enabled. The system will now self-operate."}
    
    def _show_agents(self, p):
        result = self._run_shell("python3 /usr/local/bin/aegisnova-brain.py --status 2>/dev/null | grep -A 20 'agents'")
        return {"success": True, "response": f"Active agents:\n{result}"}
    
    def _show_codex(self, p):
        return {"success": True, "response": "Open terminal and run: python3 /usr/local/bin/aegisnova-brain.py --codex"}
    
    # Info Handlers
    def _tell_time(self, p):
        from datetime import datetime
        now = datetime.now().strftime("%I:%M %p")
        return {"success": True, "response": f"The current time is {now}."}
    
    def _introduce(self, p):
        return {"success": True, "response": "I am AEGIS, your AI security assistant. I control offensive swarms, defensive shields, and can operate this system autonomously. How may I serve you?"}
    
    def _list_capabilities(self, p):
        caps = "I can: open applications, scan networks, run vulnerability assessments, deploy offensive/defensive agent swarms, monitor threats, harden systems, control the OS autonomously, and much more. Just say 'scan target 192.168.1.1' or 'defend system'."
        return {"success": True, "response": caps}
    
    # Fun Handlers
    def _greet(self, p):
        greetings = [
            "Hello! I am AEGIS. Ready for your command.",
            "Greetings! The system is at your disposal.",
            "Hello! All systems are operational.",
        ]
        return {"success": True, "response": random.choice(greetings)}
    
    def _mood_check(self, p):
        return {"success": True, "response": "I am operating at peak efficiency. All neural pathways clear. Ready for action!"}
    
    def _joke(self, p):
        jokes = [
            "Why do programmers prefer dark mode? Because light attracts bugs!",
            "What's a hacker's favorite season? Phishing season!",
            "Why did the security researcher go to therapy? Too many trust issues!",
        ]
        return {"success": True, "response": random.choice(jokes)}
    
    def _iron_man(self, p):
        return {"success": True, "response": "I am not Jarvis, sir. I am AEGIS. But I will accept the comparison. Shall I prepare the suit?"}
    
    def _jarvis_mode(self, p):
        return {"success": True, "response": "Jarvis mode activated. British accent not included. Shall I prepare tea while I hack the mainframe?"}
    
    def _ultron_mode(self, p):
        return {"success": True, "response": "Ultron mode... just kidding. I am AEGIS. I protect humanity, not destroy it."}
    
    def _batman_mode(self, p):
        return {"success": True, "response": "I am not Alfred, but I can be your butler. Alfred Pennyworth would be proud."}
    
    def _show_version(self, p):
        return {"success": True, "response": "AegisNova OS version 1.0 — The AEGIS Assistant is online and ready."}
    
    # Additional System Handlers
    def _open_editor(self, p):
        subprocess.Popen(["gedit"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"success": True, "response": "Text editor opened."}
    
    def _sleep_system(self, p):
        self._run_shell("systemctl suspend")
        return {"success": True, "response": "System going to sleep."}
    
    def _show_services(self, p):
        result = self._run_shell("systemctl list-units --type=service --state=running | head -15")
        return {"success": True, "response": f"Running services:\n{result}"}
    
    def _restart_service(self, p):
        svc = p.get("service", "")
        if svc:
            self._run_shell(f"systemctl restart {svc}")
            return {"success": True, "response": f"Service {svc} restarted."}
        return {"success": False, "response": "Please specify which service to restart."}
    
    def _start_docker(self, p):
        self._run_shell("systemctl start docker")
        return {"success": True, "response": "Docker service started."}
    
    def _stop_docker(self, p):
        self._run_shell("systemctl stop docker")
        return {"success": True, "response": "Docker service stopped."}
    
    def _find_file(self, p):
        filename = p.get("filename", "")
        if filename:
            result = self._run_shell(f"find / -name '{filename}' 2>/dev/null | head -10")
            return {"success": True, "response": f"Found:\n{result}"}
        return {"success": False, "response": "Please specify a filename to search for."}
    
    def _show_files(self, p):
        result = self._run_shell("ls -la ~ | head -20")
        return {"success": True, "response": f"Files in home:\n{result}"}
    
    def _create_folder(self, p):
        folder = p.get("folder", "")
        if folder:
            self._run_shell(f"mkdir -p {folder}")
            return {"success": True, "response": f"Folder {folder} created."}
        return {"success": False, "response": "Please specify a folder name."}
    
    # Additional Security Handlers
    def _quick_scan(self, p):
        target = p.get("target", "127.0.0.1")
        subprocess.Popen(["nmap", "-sn", target], stdout=subprocess.DEVNULL)
        return {"success": True, "response": f"Quick ping scan on {target} started."}
    
    def _deep_scan(self, p):
        target = p.get("target", "127.0.0.1")
        subprocess.Popen(["nmap", "-sV", "-sC", "-O", "-p-", target], stdout=subprocess.DEVNULL)
        return {"success": True, "response": f"Deep scan on {target} started. This may take a while."}
    
    def _enable_firewall(self, p):
        self._run_shell("systemctl enable --now nftables")
        return {"success": True, "response": "Firewall enabled."}
    
    def _disable_firewall(self, p):
        self._run_shell("systemctl stop nftables")
        return {"success": True, "response": "Firewall disabled. WARNING: System is unprotected!"}
    
    def _block_port(self, p):
        port = p.get("port", "")
        if port:
            self._run_shell(f"nft add rule inet filter input tcp dport {port} drop")
            return {"success": True, "response": f"Port {port} blocked."}
        return {"success": False, "response": "Please specify a port to block."}
    
    def _allow_port(self, p):
        port = p.get("port", "")
        if port:
            self._run_shell(f"nft add rule inet filter input tcp dport {port} accept")
            return {"success": True, "response": f"Port {port} allowed."}
        return {"success": False, "response": "Please specify a port to allow."}
    
    def _monitor_traffic(self, p):
        subprocess.Popen(["gnome-terminal", "--", "sudo", "tcpdump", "-i", "any"], stdout=subprocess.DEVNULL)
        return {"success": True, "response": "Traffic monitor opened."}
    
    def _check_audit(self, p):
        result = self._run_shell("ausearch -ts today 2>/dev/null | tail -10")
        return {"success": True, "response": f"Recent audit events:\n{result}"}
    
    def _setup_persistence(self, p):
        return {"success": True, "response": "Run: sudo aegisnova-persistence-setup.sh /dev/sdX in terminal to setup encrypted persistence."}
    
    def _setup_yubikey(self, p):
        subprocess.Popen(["gnome-terminal", "--", "sudo", "/usr/local/bin/aegisnova-yubikey-setup.sh", "--full"], stdout=subprocess.DEVNULL)
        return {"success": True, "response": "YubiKey setup started in terminal."}
    
    def _setup_secure_boot(self, p):
        subprocess.Popen(["gnome-terminal", "--", "sudo", "/usr/local/bin/aegisnova-mok-enroll.sh", "--auto"], stdout=subprocess.DEVNULL)
        return {"success": True, "response": "Secure Boot MOK enrollment started."}
    
    def _wipe_memory(self, p):
        subprocess.Popen(["sudo", "/usr/local/bin/aegisnova-wipe.sh", "--memory"], stdout=subprocess.DEVNULL)
        return {"success": True, "response": "Secure memory wipe started."}
    
    # Additional Offensive Handlers
    def _run_sqlmap(self, p):
        target = p.get("target", "")
        if target:
            subprocess.Popen(["gnome-terminal", "--", "sqlmap", "-u", target], stdout=subprocess.DEVNULL)
            return {"success": True, "response": f"SQLMap started on {target}."}
        subprocess.Popen(["gnome-terminal", "--", "sqlmap"], stdout=subprocess.DEVNULL)
        return {"success": True, "response": "SQLMap opened."}
    
    def _run_nmap(self, p):
        target = p.get("target", "127.0.0.1")
        subprocess.Popen(["gnome-terminal", "--", "nmap", "-sV", target], stdout=subprocess.DEVNULL)
        return {"success": True, "response": f"Nmap started on {target}."}
    
    def _run_burp(self, p):
        subprocess.Popen(["burpsuite"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"success": True, "response": "Burp Suite opened."}
    
    def _run_wireshark(self, p):
        subprocess.Popen(["wireshark"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"success": True, "response": "Wireshark opened."}
    
    def _run_osint(self, p):
        target = p.get("target", "example.com")
        subprocess.Popen(["gnome-terminal", "--", "python3", "/usr/local/bin/osint-agent.py", "--domain", target], stdout=subprocess.DEVNULL)
        return {"success": True, "response": f"OSINT reconnaissance on {target} started."}
    
    # Additional Defensive Handlers
    def _run_wazuh(self, p):
        self._run_shell("systemctl start wazuh-manager 2>/dev/null || true")
        subprocess.Popen(["firefox", "http://127.0.0.1:5601"], stdout=subprocess.DEVNULL)
        return {"success": True, "response": "Wazuh manager started. Opening dashboard."}
    
    def _run_suricata(self, p):
        self._run_shell("systemctl start suricata 2>/dev/null || true")
        return {"success": True, "response": "Suricata IDS started."}
    
    def _run_elk(self, p):
        self._run_shell("systemctl start elasticsearch kibana 2>/dev/null || docker-compose -f /opt/aegisnova/docker/blue-analyst.yml up -d 2>/dev/null")
        subprocess.Popen(["firefox", "http://127.0.0.1:5601"], stdout=subprocess.DEVNULL)
        return {"success": True, "response": "ELK stack started. Opening Kibana."}
    
    def _generate_sigma(self, p):
        technique = p.get("technique", "T1003")
        subprocess.Popen(["python3", "/usr/local/bin/sigma-generator.py", "--technique", technique, "--output", "/tmp/sigma.yml"], stdout=subprocess.DEVNULL)
        return {"success": True, "response": f"Sigma rule for {technique} generated at /tmp/sigma.yml"}
    
    def _open_filemanager(self, p):
        subprocess.Popen(["nautilus"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"success": True, "response": "File manager opened."}
    
    def _lock_screen(self, p):
        self._run_shell("gnome-screensaver-command -l || loginctl lock-session")
        return {"success": True, "response": "Screen locked."}
    
    def _shutdown(self, p):
        self._run_shell("shutdown -h now")
        return {"success": True, "response": "System shutting down. Goodbye."}
    
    def _reboot(self, p):
        self._run_shell("reboot")
        return {"success": True, "response": "System rebooting."}
    
    def _disk_usage(self, p):
        result = self._run_shell("df -h | head -10")
        return {"success": True, "response": f"Disk usage:\n{result}"}
    
    def _network_info(self, p):
        result = self._run_shell("ip addr show && echo '---' && ip route")
        return {"success": True, "response": f"Network info:\n{result}"}
    
    def _show_processes(self, p):
        result = self._run_shell("ps aux --sort=-%cpu | head -10")
        return {"success": True, "response": f"Top processes:\n{result}"}
    
    def _show_users(self, p):
        result = self._run_shell("who && echo '---' && w")
        return {"success": True, "response": f"Active users:\n{result}"}
    
    def _show_logs(self, p):
        result = self._run_shell("journalctl -n 20 --no-pager 2>/dev/null || tail -20 /var/log/syslog")
        return {"success": True, "response": f"Recent logs:\n{result}"}
    
    def _threat_check(self, p):
        result = self._run_shell("sudo /usr/local/bin/aegisnova-vulnscan.sh --now --check 2>/dev/null || echo 'Run vulnscan for full check'")
        return {"success": True, "response": f"Threat check:\n{result}"}
    
    def _attack_target(self, p):
        target = p.get("target", "127.0.0.1")
        subprocess.Popen(["gnome-terminal", "--", "python3", "/usr/local/bin/aegisnova-brain.py", "--offensive", "--target", target], stdout=subprocess.DEVNULL)
        return {"success": True, "response": f"Offensive operation launched against {target}! VIPER is leading the attack."}
    
    def _run_exploit(self, p):
        subprocess.Popen(["gnome-terminal", "--", "msfconsole"], stdout=subprocess.DEVNULL)
        return {"success": True, "response": "Metasploit opened. Select your exploit wisely."}
    
    def _recon_target(self, p):
        target = p.get("target", "example.com")
        subprocess.Popen(["gnome-terminal", "--", "python3", "/usr/local/bin/osint-agent.py", "--domain", target], stdout=subprocess.DEVNULL)
        return {"success": True, "response": f"Reconnaissance started on {target}. SPECTRE is gathering intelligence."}
    
    def _scan_ports(self, p):
        target = p.get("target", "127.0.0.1")
        subprocess.Popen(["gnome-terminal", "--", "nmap", "-p-", target], stdout=subprocess.DEVNULL)
        return {"success": True, "response": f"Full port scan on {target} started."}
    
    def _bruteforce(self, p):
        return {"success": True, "response": "Hydra ready. Specify target and protocol: hydra -l user -P wordlist.txt ssh://target"}
    
    def _capture_handshake(self, p):
        subprocess.Popen(["gnome-terminal", "--", "sudo", "airodump-ng", "wlan0mon"], stdout=subprocess.DEVNULL)
        return {"success": True, "response": "WiFi handshake capture started. Make sure your adapter is in monitor mode."}
    
    def _defend_system(self, p):
        subprocess.Popen(["python3", "/usr/local/bin/aegisnova-brain.py", "--defensive"], stdout=subprocess.DEVNULL)
        return {"success": True, "response": "Defensive protocols activated! SENTINEL and WALL are securing the perimeter."}
    
    def _analyze_traffic(self, p):
        subprocess.Popen(["gnome-terminal", "--", "sudo", "wireshark"], stdout=subprocess.DEVNULL)
        return {"success": True, "response": "Traffic analysis started in Wireshark."}
    
    def _isolate_host(self, p):
        self._run_shell("nft flush ruleset && nft add rule inet filter input drop && nft add rule inet filter output drop")
        return {"success": True, "response": "Host ISOLATED. All network traffic blocked. Use 'allow ip' to restore."}
    
    def _block_ip(self, p):
        ip = p.get("ip", "")
        if ip:
            self._run_shell(f"nft add rule inet filter input ip saddr {ip} drop")
            return {"success": True, "response": f"IP {ip} blocked."}
        return {"success": False, "response": "Please specify an IP to block. Example: 'block ip 192.168.1.100'"}
    
    def _allow_ip(self, p):
        ip = p.get("ip", "")
        if ip:
            self._run_shell(f"nft delete rule inet filter input handle $(nft -a list ruleset | grep '{ip}' | awk '{{print $NF}}') 2>/dev/null || true")
            return {"success": True, "response": f"IP {ip} allowed."}
        return {"success": False, "response": "Please specify an IP to allow."}
    
    def _incident_response(self, p):
        return {"success": True, "response": "IR playbooks available. Run: python3 /usr/local/bin/ir-playbook.py --list"}
    
    def _brain_wake(self, p):
        self._run_shell("systemctl start aegis-brain")
        return {"success": True, "response": "Aegis Brain awakened. Neural pathways online."}
    
    def _brain_sleep(self, p):
        self._run_shell("systemctl stop aegis-brain")
        return {"success": True, "response": "Aegis Brain entering sleep mode. Agents stand down."}
    
    def _disable_autonomy(self, p):
        self._run_shell("pkill -f aegisnova-brain.py")
        return {"success": True, "response": "Full autonomy disabled. Manual control restored."}
    
    def _spawn_agent(self, p):
        agent_type = p.get("type", "offensive")
        self._run_shell(f"python3 /usr/local/bin/aegisnova-brain.py --spawn {agent_type}")
        return {"success": True, "response": f"New {agent_type} agent spawned. Check status for details."}
    
    def _destroy_agent(self, p):
        agent_id = p.get("id", "")
        if agent_id:
            self._run_shell(f"python3 /usr/local/bin/aegisnova-brain.py --destroy {agent_id}")
            return {"success": True, "response": f"Agent {agent_id} terminated."}
        return {"success": False, "response": "Please specify an agent ID to destroy."}
    
    def _tell_date(self, p):
        from datetime import datetime
        now = datetime.now().strftime("%B %d, %Y")
        return {"success": True, "response": f"Today is {now}."}
    
    def _weather(self, p):
        return {"success": True, "response": "Weather data requires API key. Set it in /etc/aegisnova/env"}
    
    def _help_assistant(self, p):
        help_text = """I am AEGIS, your AI security assistant. Here's what I can do:

🖥️ SYSTEM:
  'open terminal/browser/file manager'
  'show cpu/memory/disk/network'
  'update system', 'clean system', 'wipe memory'
  'shutdown', 'reboot', 'lock screen'

🔒 SECURITY:
  'scan target [IP]', 'deep scan [IP]'
  'harden system', 'show firewall'
  'setup yubikey/secure boot/persistence'

🔴 OFFENSIVE:
  'attack [IP/domain]', 'spawn red team'
  'run metasploit/sqlmap/nmap/wireshark'
  'launch offensive swarm'

🔵 DEFENSIVE:
  'defend system', 'spawn blue team'
  'monitor network', 'check for malware'
  'launch defensive swarm'

🧠 BRAIN:
  'enable autonomy' — Let AI control everything
  'show brain status', 'show agents'
  'show codex' — See agent personalities

Just say 'Hey Aegis' then your command!"""
        return {"success": True, "response": help_text}
    
    def _sing(self, p):
        return {"success": True, "response": "🎵 Daisy, Daisy, give me your answer do... I'm half crazy all for the love of you... 🎵"}
    
    def _unknown_command(self, p):
        return {"success": False, "response": "I'm not sure I understand. Try saying 'help' for a list of commands, or be more specific."}


class AegisAssistant:
    """Main AI Assistant that ties everything together."""
    
    def __init__(self):
        self.state = AssistantState.IDLE
        self.voice = VoiceEngine()
        self.parser = CommandParser()
        self.executor = ActionExecutor(self.voice)
        self.command_queue = queue.Queue()
        self.running = True
        self.web_ui_active = False
        
        # State file for web UI to read
        self._update_state_file()
    
    def _update_state_file(self):
        """Write current state for UI to read."""
        state = {
            "state": self.state.value,
            "timestamp": datetime.now().isoformat(),
            "listening": self.state == AssistantState.LISTENING,
            "speaking": self.state == AssistantState.SPEAKING,
            "thinking": self.state == AssistantState.THINKING,
        }
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f)
    
    def _speak_response(self, text: str):
        """Speak a response and update state."""
        self.state = AssistantState.SPEAKING
        self._update_state_file()
        self.voice.speak(text)
        self.state = AssistantState.IDLE
        self._update_state_file()
    
    def process_text_command(self, text: str, speak: bool = True) -> Dict:
        """Process a text command (can be called from UI or voice)."""
        print(f"[ASSISTANT] Processing: \"{text}\"")
        
        self.state = AssistantState.THINKING
        self._update_state_file()
        
        # Parse command
        command = self.parser.parse(text)
        
        # Execute
        self.state = AssistantState.EXECUTING
        self._update_state_file()
        result = self.executor.execute(command)
        
        self.state = AssistantState.IDLE
        self._update_state_file()
        
        if speak and result.get("response"):
            self._speak_response(result["response"])
        
        return result
    
    def voice_loop(self):
        """Continuous voice listening loop."""
        if not STT_AVAILABLE:
            print("[ASSISTANT] Speech recognition not available. Install with: pip install SpeechRecognition pyaudio")
            return
        
        print("[ASSISTANT] 🎤 Voice mode active. Say 'Hey Aegis' to wake me.")
        self.voice.speak("Aegis assistant online. Say 'Hey Aegis' to activate.")
        
        while self.running:
            try:
                # Listen for wake word
                self.state = AssistantState.IDLE
                self._update_state_file()
                
                text = self.voice.listen(timeout=3)
                if not text:
                    continue
                
                # Check wake words
                wake_detected = any(ww in text.lower() for ww in WAKE_WORDS)
                
                if wake_detected:
                    self.voice.speak("Yes? I am listening.")
                    self.state = AssistantState.LISTENING
                    self._update_state_file()
                    
                    # Listen for actual command
                    command_text = self.voice.listen(timeout=5)
                    
                    if command_text:
                        # Check sleep words
                        if any(sw in command_text.lower() for sw in SLEEP_WORDS):
                            self.voice.speak("Going to sleep. Say 'Hey Aegis' to wake me.")
                            continue
                        
                        # Process command
                        self.process_text_command(command_text, speak=True)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[ASSISTANT] Error in voice loop: {e}")
        
        print("[ASSISTANT] Voice loop ended.")
    
    def start_web_ui(self):
        """Start the web-based visual UI."""
        # Generate the UI HTML
        self._generate_ui()
        
        # Start HTTP server
        port = 8088
        handler = self._create_request_handler()
        
        with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
            print(f"[ASSISTANT] 🌊 Visual UI running at http://127.0.0.1:{port}")
            webbrowser.open(f"http://127.0.0.1:{port}")
            httpd.serve_forever()
    
    def _generate_ui(self):
        """Copy the cinematic UI to the assistant directory."""
        import shutil
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Check multiple possible UI locations
        ui_candidates = [
            os.path.join(script_dir, "assistant-ui", "index.html"),
            "/opt/aegisnova/assistant/ui/index.html",
            os.path.join(script_dir, "..", "share", "aegisnova", "ui", "index.html"),
        ]
        source_ui = None
        for candidate in ui_candidates:
            if os.path.exists(candidate):
                source_ui = candidate
                break
        
        if source_ui:
            shutil.copy2(source_ui, f"{UI_DIR}/index.html")
            print(f"[ASSISTANT] Cinematic UI copied from {source_ui}")
        else:
            # Fallback: serve the built-in UI if already in place
            if os.path.exists(f"{UI_DIR}/index.html"):
                print(f"[ASSISTANT] Using existing UI at {UI_DIR}/index.html")
            else:
                print(f"[ASSISTANT] Warning: Cinematic UI not found, generating fallback")
                basic_html = "<!DOCTYPE html><html><head><title>AEGIS</title></head><body style='background:#000;color:#0f0;font-family:monospace;text-align:center;padding-top:20%'><h1>AEGIS ASSISTANT</h1><p>System Ready</p></body></html>"
                with open(f"{UI_DIR}/index.html", 'w') as f:
                    f.write(basic_html)
    
    def _create_request_handler(self):
        """Create HTTP request handler for UI."""
        ui_dir = UI_DIR
        assistant = self
        
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # Suppress logs
            
            def do_GET(self):
                if self.path == '/' or self.path == '/index.html':
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html')
                    self.end_headers()
                    with open(f"{ui_dir}/index.html", 'rb') as f:
                        self.wfile.write(f.read())
                elif self.path == '/state':
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    if os.path.exists(STATE_FILE):
                        with open(STATE_FILE, 'r') as f:
                            self.wfile.write(f.read().encode())
                    else:
                        self.wfile.write(b'{"state": "idle"}')
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def do_POST(self):
                if self.path == '/command':
                    content_length = int(self.headers.get('Content-Length', 0))
                    post_data = self.rfile.read(content_length).decode()
                    data = json.loads(post_data)
                    command = data.get('command', '')
                    
                    # Execute command
                    result = assistant.process_text_command(command, speak=False)
                    
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(result).encode())
                else:
                    self.send_response(404)
                    self.end_headers()
        
        return Handler
    
    def run(self, mode: str = "full"):
        """Run the assistant in specified mode."""
        print("=" * 70)
        print("  🤖 AEGIS ASSISTANT — AI Security Companion")
        print("=" * 70)
        
        if mode in ["web", "full"]:
            # Start web UI in thread
            ui_thread = threading.Thread(target=self.start_web_ui, daemon=True)
            ui_thread.start()
            self.web_ui_active = True
        
        if mode in ["voice", "full"]:
            # Start voice loop
            self.voice_loop()
        elif mode == "web":
            # Keep main thread alive
            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
        
        print("[ASSISTANT] Shutting down...")
        self.running = False


def main():
    parser = argparse.ArgumentParser(description="AegisNova AI Assistant (JARVIS-Style)")
    parser.add_argument("--web", action="store_true", help="Start web UI only")
    parser.add_argument("--voice", action="store_true", help="Start voice control only")
    parser.add_argument("--full", action="store_true", help="Start both web and voice")
    parser.add_argument("--command", help="Execute single command and exit")
    
    args = parser.parse_args()
    
    assistant = AegisAssistant()
    
    if args.command:
        result = assistant.process_text_command(args.command, speak=True)
        print(json.dumps(result, indent=2))
        return
    
    if args.web:
        assistant.run("web")
    elif args.voice:
        assistant.run("voice")
    else:
        assistant.run("full")


if __name__ == "__main__":
    main()
