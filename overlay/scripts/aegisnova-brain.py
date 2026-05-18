#!/usr/bin/env python3
"""
AegisNova OS — AEGIS BRAIN (Master AI Orchestrator)
=====================================================
The "Live Brain" of AegisNova OS. A self-evolving, multi-agent system
that autonomously operates the entire OS.

Capabilities:
- Spawns specialized agents on-demand (Army of Agents)
- Self-orchestrates offensive/defensive operations
- Learns from results and creates new strategies
- Direct OS-level control and automation
- Inter-agent communication and coordination
- Dynamic agent lifecycle management (create/destroy/upgrade)

Usage:
    python3 aegisnova-brain.py --mode autonomous
    python3 aegisnova-brain.py --mission "pentest 192.168.1.0/24"
    python3 aegisnova-brain.py --swarm-defense
    python3 aegisnova-brain.py --os-autopilot
"""

import os
import sys
import time
import json
import uuid
import random
import signal
import subprocess
import threading
import argparse
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import queue

# Import agent codex
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from brain_agent_codex import get_random_personality, ALL_PERSONALITIES
    CODEX_AVAILABLE = True
except ImportError as e:
    print(f"[BRAIN] Codex not loaded: {e}")
    CODEX_AVAILABLE = False

# ── Configuration ──
BRAIN_DIR = "/opt/aegisnova/brain"
AGENT_REGISTRY = f"{BRAIN_DIR}/agents.json"
MISSION_LOG = f"{BRAIN_DIR}/missions.log"
LEARNED_DIR = f"{BRAIN_DIR}/learned"
BUS_DIR = f"{BRAIN_DIR}/bus"
MAX_AGENTS = 50  # Maximum concurrent agents

os.makedirs(BRAIN_DIR, exist_ok=True)
os.makedirs(LEARNED_DIR, exist_ok=True)
os.makedirs(BUS_DIR, exist_ok=True)

class AgentType(Enum):
    OFFENSIVE = "offensive"      # Red team operations
    DEFENSIVE = "defensive"      # Blue team operations
    OS_CONTROL = "os_control"    # System automation
    RECON = "recon"              # Intelligence gathering
    EXPLOIT = "exploit"           # Exploitation
    PIVOT = "pivot"               # Lateral movement
    PERSIST = "persist"           # Persistence
    EVADE = "evade"               # Defense evasion
    DETECT = "detect"             # Threat detection
    RESPOND = "respond"           # Incident response
    HUNT = "hunt"                 # Threat hunting
    CUSTOM = "custom"             # User-defined

class AgentStatus(Enum):
    SPAWNING = "spawning"
    ACTIVE = "active"
    BUSY = "busy"
    IDLE = "idle"
    DYING = "dying"
    DEAD = "dead"

class MissionType(Enum):
    OFFENSIVE_OPERATION = "offensive_op"
    DEFENSIVE_OPERATION = "defensive_op"
    OS_AUTOMATION = "os_auto"
    THREAT_HUNT = "threat_hunt"
    INCIDENT_RESPONSE = "incident_response"
    FULL_AUTONOMY = "full_autonomy"

@dataclass
class Agent:
    """Represents a spawned agent instance."""
    id: str
    name: str
    agent_type: AgentType
    status: AgentStatus
    pid: Optional[int]
    capabilities: List[str]
    target: Optional[str]
    created_at: str
    last_activity: str
    mission_id: Optional[str]
    parent_id: Optional[str]
    children: List[str] = field(default_factory=list)
    results: List[Dict] = field(default_factory=list)
    learnings: List[str] = field(default_factory=list)
    # Personality fields
    callsign: str = "UNKNOWN"
    personality: str = ""
    voice: str = "neutral"
    specialty: str = ""
    quote: str = ""
    
    def speak(self, message: str, level: str = "INFO"):
        """Agent speaks in its unique voice."""
        prefix = f"[{self.callsign}]"
        if self.voice == "terse":
            print(f"{prefix} {message[:60]}")
        elif self.voice == "minimal":
            print(f"{prefix} ...")
        elif self.voice == "energetic":
            print(f"{prefix} ⚡ {message.upper()}!")
        elif self.voice == "authoritative":
            print(f"{prefix} ■ {message}")
        elif self.voice == "cryptic":
            print(f"{prefix} ~ {message[:40]}... [redacted]")
        elif self.voice == "robotic":
            print(f"{prefix} [EXEC] {message}")
        elif self.voice == "mysterious":
            print(f"{prefix} ??? {message}")
        else:
            print(f"{prefix} {message}")

@dataclass
class Mission:
    """Represents an active mission."""
    id: str
    mission_type: MissionType
    description: str
    status: str
    agents: List[str]
    target: Optional[str]
    objectives: List[str]
    results: List[Dict]
    created_at: str
    completed_at: Optional[str]

class InterAgentBus:
    """Message bus for inter-agent communication."""
    
    def __init__(self):
        self.messages = queue.Queue()
        self.subscribers: Dict[str, List[Callable]] = {}
        self.lock = threading.Lock()
    
    def publish(self, channel: str, message: Dict):
        """Publish message to a channel."""
        msg = {
            "id": str(uuid.uuid4())[:8],
            "channel": channel,
            "timestamp": datetime.utcnow().isoformat(),
            "data": message
        }
        
        # Write to file-based bus for persistence
        bus_file = f"{BUS_DIR}/{channel}.jsonl"
        with open(bus_file, 'a') as f:
            f.write(json.dumps(msg) + '\n')
        
        # Notify subscribers
        with self.lock:
            for callback in self.subscribers.get(channel, []):
                try:
                    callback(msg)
                except Exception as e:
                    pass
    
    def subscribe(self, channel: str, callback: Callable):
        """Subscribe to a channel."""
        with self.lock:
            if channel not in self.subscribers:
                self.subscribers[channel] = []
            self.subscribers[channel].append(callback)
    
    def get_messages(self, channel: str, limit: int = 100) -> List[Dict]:
        """Get recent messages from a channel."""
        bus_file = f"{BUS_DIR}/{channel}.jsonl"
        if not os.path.exists(bus_file):
            return []
        
        messages = []
        with open(bus_file, 'r') as f:
            for line in f.readlines()[-limit:]:
                try:
                    messages.append(json.loads(line))
                except:
                    pass
        return messages

class AgentFactory:
    """Dynamically creates agent instances based on mission needs."""
    
    def __init__(self, bus: InterAgentBus):
        self.bus = bus
        self.agent_counter = 0
    
    def spawn(self, agent_type: AgentType, mission_id: str, 
              parent_id: Optional[str] = None, target: Optional[str] = None,
              custom_caps: Optional[List[str]] = None) -> Agent:
        """Spawn a new agent instance with personality."""
        self.agent_counter += 1
        agent_id = f"{agent_type.value[:3]}-{uuid.uuid4().hex[:6]}"
        
        caps = custom_caps or self._get_default_capabilities(agent_type)
        
        # Get personality from codex
        personality_data = {}
        if CODEX_AVAILABLE:
            try:
                personality_data = get_random_personality(agent_type.value)
            except:
                pass
        
        agent = Agent(
            id=agent_id,
            name=f"{agent_type.value}-{self.agent_counter}",
            agent_type=agent_type,
            status=AgentStatus.SPAWNING,
            pid=None,
            capabilities=caps,
            target=target,
            created_at=datetime.utcnow().isoformat(),
            last_activity=datetime.utcnow().isoformat(),
            mission_id=mission_id,
            parent_id=parent_id,
            children=[],
            results=[],
            learnings=[],
            callsign=personality_data.get("callsign", f"AGENT-{self.agent_counter}"),
            personality=personality_data.get("personality", ""),
            voice=personality_data.get("voice", "neutral"),
            specialty=personality_data.get("specialty", ""),
            quote=personality_data.get("quote", "Ready.")
        )
        
        # Launch agent process
        agent.status = AgentStatus.ACTIVE
        
        # Agent introduction
        print(f"\n  🎯 AGENT DEPLOYED: {agent.callsign}")
        print(f"     Role: {personality_data.get('name', agent.agent_type.value)}")
        print(f"     Specialty: {agent.specialty}")
        print(f'     "{agent.quote}"')
        print(f"     Mission: {mission_id}")
        
        self.bus.publish("brain.events", {
            "event": "agent_spawned",
            "agent_id": agent_id,
            "callsign": agent.callsign,
            "type": agent_type.value,
            "mission": mission_id,
            "parent": parent_id,
            "quote": agent.quote
        })
        
        return agent
    
    def _get_default_capabilities(self, agent_type: AgentType) -> List[str]:
        caps = {
            AgentType.OFFENSIVE: ["nmap", "exploit", "payload", "c2", "pivot"],
            AgentType.DEFENSIVE: ["monitor", "detect", "alert", "block", "isolate"],
            AgentType.OS_CONTROL: ["exec", "configure", "update", "harden", "audit"],
            AgentType.RECON: ["scan", "enumerate", "osint", "dns", "whois"],
            AgentType.EXPLOIT: ["msf", "sqlmap", "xss", "rce", "privesc"],
            AgentType.PIVOT: ["tunnel", "proxy", "portfwd", "socks"],
            AgentType.PERSIST: ["cron", "service", "backdoor", "registry"],
            AgentType.EVADE: ["obfuscate", "encrypt", "stego", "anti-forensics"],
            AgentType.DETECT: ["yara", "sigma", "logs", "traffic", "behavior"],
            AgentType.RESPOND: ["isolate", "contain", "eradicate", "recover"],
            AgentType.HUNT: ["ioc", "ttp", "timeline", "correlation", "ml-detect"],
            AgentType.CUSTOM: []
        }
        return caps.get(agent_type, [])

class AegisBrain:
    """
    The Master AI Brain of AegisNova OS.
    
    Capabilities:
    - Continuous OS monitoring and decision making
    - Dynamic agent spawning for tasks
    - Mission planning and decomposition
    - Self-improvement through learning loops
    - Full autonomous operation mode
    """
    
    def __init__(self):
        self.bus = InterAgentBus()
        self.factory = AgentFactory(self.bus)
        self.agents: Dict[str, Agent] = {}
        self.missions: Dict[str, Mission] = {}
        self.running = True
        self.max_agents = MAX_AGENTS
        self.learned_strategies: List[Dict] = self._load_learned()
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)
        
        # Subscribe to agent events
        self.bus.subscribe("agent.events", self._handle_agent_event)
        self.bus.subscribe("mission.complete", self._handle_mission_complete)
    
    def _load_learned(self) -> List[Dict]:
        """Load previously learned strategies."""
        learned_file = f"{LEARNED_DIR}/strategies.json"
        if os.path.exists(learned_file):
            with open(learned_file, 'r') as f:
                return json.load(f)
        return []
    
    def _save_learned(self):
        """Save learned strategies."""
        learned_file = f"{LEARNED_DIR}/strategies.json"
        with open(learned_file, 'w') as f:
            json.dump(self.learned_strategies, f, indent=2)
    
    def _shutdown(self, signum, frame):
        log = lambda msg: print(f"[BRAIN] {msg}")
        log("Shutting down Aegis Brain...")
        self.running = False
        
        # Kill all spawned agents
        for agent in list(self.agents.values()):
            agent.status = AgentStatus.DYING
            if agent.pid:
                try:
                    os.kill(agent.pid, signal.SIGTERM)
                except:
                    pass
        
        self._save_learned()
        log("All agents terminated. Brain stopped.")
    
    def _handle_agent_event(self, message: Dict):
        """Handle events from agents."""
        data = message.get("data", {})
        event_type = data.get("event", "")
        agent_id = data.get("agent_id", "")
        
        if event_type == "task_complete" and agent_id in self.agents:
            agent = self.agents[agent_id]
            agent.results.append(data.get("result", {}))
            agent.last_activity = datetime.utcnow().isoformat()
            
            # Check if agent learned something new
            if data.get("learning"):
                agent.learnings.append(data["learning"])
                self._integrate_learning(data["learning"])
    
    def _handle_mission_complete(self, message: Dict):
        """Handle mission completion."""
        data = message.get("data", {})
        mission_id = data.get("mission_id", "")
        
        if mission_id in self.missions:
            mission = self.missions[mission_id]
            mission.status = "completed"
            mission.completed_at = datetime.utcnow().isoformat()
            mission.results = data.get("results", [])
            
            # Save mission log
            with open(MISSION_LOG, 'a') as f:
                f.write(json.dumps(asdict(mission)) + '\n')
            
            # Learn from mission
            self._learn_from_mission(mission)
    
    def _integrate_learning(self, learning: str):
        """Integrate new learning into strategies."""
        if learning not in [s.get("pattern") for s in self.learned_strategies]:
            self.learned_strategies.append({
                "pattern": learning,
                "learned_at": datetime.utcnow().isoformat(),
                "uses": 0,
                "success_rate": 0.0
            })
            self._save_learned()
    
    def _learn_from_mission(self, mission: Mission):
        """Extract learnings from completed mission."""
        # Analyze what worked and what didn't
        for result in mission.results:
            if result.get("success"):
                strategy = result.get("strategy", "")
                if strategy:
                    self._integrate_learning(strategy)
    
    def spawn_agent(self, agent_type: AgentType, mission_id: str, 
                    parent_id: Optional[str] = None, target: Optional[str] = None,
                    custom_caps: Optional[List[str]] = None) -> Optional[Agent]:
        """Spawn a new agent if under limit."""
        active_count = len([a for a in self.agents.values() 
                          if a.status in [AgentStatus.ACTIVE, AgentStatus.BUSY]])
        
        if active_count >= self.max_agents:
            print(f"[BRAIN] Agent limit reached ({self.max_agents}). Cannot spawn more.")
            return None
        
        agent = self.factory.spawn(agent_type, mission_id, parent_id, target, custom_caps)
        self.agents[agent.id] = agent
        
        # If has parent, register as child
        if parent_id and parent_id in self.agents:
            self.agents[parent_id].children.append(agent.id)
        
        return agent
    
    def create_mission(self, mission_type: MissionType, description: str,
                       target: Optional[str] = None,
                       objectives: Optional[List[str]] = None) -> Mission:
        """Create a new mission."""
        mission_id = f"M-{uuid.uuid4().hex[:8]}"
        mission = Mission(
            id=mission_id,
            mission_type=mission_type,
            description=description,
            status="planning",
            agents=[],
            target=target,
            objectives=objectives or [],
            results=[],
            created_at=datetime.utcnow().isoformat(),
            completed_at=None
        )
        self.missions[mission_id] = mission
        return mission
    
    def plan_offensive_operation(self, target: str, scope: str = "full") -> Mission:
        """
        Plan and execute an autonomous offensive operation.
        Spawns recon → exploit → pivot → persist → evade agents.
        """
        mission = self.create_mission(
            MissionType.OFFENSIVE_OPERATION,
            f"Autonomous offensive operation against {target}",
            target=target,
            objectives=["recon", "vuln-identify", "exploit", "pivot", "persist", "exfil-test"]
        )
        
        # Phase 1: Reconnaissance
        print(f"[BRAIN] Phase 1: Deploying reconnaissance swarm...")
        recon = self.spawn_agent(AgentType.RECON, mission.id, target=target)
        if recon:
            mission.agents.append(recon.id)
            self._execute_recon(recon, target, scope)
        
        # Phase 2: Exploitation (spawns based on recon results)
        print(f"[BRAIN] Phase 2: Deploying exploitation agents...")
        exploit = self.spawn_agent(AgentType.EXPLOIT, mission.id, 
                                   parent_id=recon.id if recon else None,
                                   target=target)
        if exploit:
            mission.agents.append(exploit.id)
        
        # Phase 3: Lateral movement
        print(f"[BRAIN] Phase 3: Deploying pivot agents...")
        pivot = self.spawn_agent(AgentType.PIVOT, mission.id,
                                parent_id=exploit.id if exploit else None,
                                target=target)
        if pivot:
            mission.agents.append(pivot.id)
        
        # Phase 4: Persistence
        print(f"[BRAIN] Phase 4: Deploying persistence agents...")
        persist = self.spawn_agent(AgentType.PERSIST, mission.id,
                                  parent_id=pivot.id if pivot else None,
                                  target=target)
        if persist:
            mission.agents.append(persist.id)
        
        # Phase 5: Evasion
        print(f"[BRAIN] Phase 5: Deploying evasion agents...")
        evade = self.spawn_agent(AgentType.EVADE, mission.id,
                                parent_id=persist.id if persist else None,
                                target=target)
        if evade:
            mission.agents.append(evade.id)
        
        mission.status = "active"
        print(f"[BRAIN] Offensive operation {mission.id} launched with {len(mission.agents)} agents!")
        return mission
    
    def plan_defensive_operation(self, scope: str = "network") -> Mission:
        """
        Plan and execute an autonomous defensive operation.
        Spawns detect → hunt → respond → harden agents.
        """
        mission = self.create_mission(
            MissionType.DEFENSIVE_OPERATION,
            f"Autonomous defensive operation ({scope})",
            objectives=["monitor", "detect", "hunt", "respond", "harden"]
        )
        
        # Phase 1: Detection
        print(f"[BRAIN] Phase 1: Deploying detection swarm...")
        detect = self.spawn_agent(AgentType.DETECT, mission.id)
        if detect:
            mission.agents.append(detect.id)
            self._execute_detection(detect, scope)
        
        # Phase 2: Threat Hunting
        print(f"[BRAIN] Phase 2: Deploying threat hunters...")
        hunt = self.spawn_agent(AgentType.HUNT, mission.id,
                               parent_id=detect.id if detect else None)
        if hunt:
            mission.agents.append(hunt.id)
        
        # Phase 3: Response
        print(f"[BRAIN] Phase 3: Deploying incident responders...")
        respond = self.spawn_agent(AgentType.RESPOND, mission.id,
                                  parent_id=hunt.id if hunt else None)
        if respond:
            mission.agents.append(respond.id)
        
        # Phase 4: OS Control (hardening)
        print(f"[BRAIN] Phase 4: Deploying hardening agents...")
        os_control = self.spawn_agent(AgentType.OS_CONTROL, mission.id)
        if os_control:
            mission.agents.append(os_control.id)
            self._execute_hardening(os_control)
        
        mission.status = "active"
        print(f"[BRAIN] Defensive operation {mission.id} launched with {len(mission.agents)} agents!")
        return mission
    
    def plan_full_autonomy(self) -> Mission:
        """
        Enable full OS autonomy — the brain controls everything.
        Monitors system, spawns agents as needed, learns continuously.
        """
        mission = self.create_mission(
            MissionType.FULL_AUTONOMY,
            "Full autonomous operation mode",
            objectives=["monitor", "self-protect", "optimize", "learn"]
        )
        
        print(f"[BRAIN] 🧠 ACTIVATING FULL AUTONOMY MODE 🧠")
        print(f"[BRAIN] The system will now self-operate and self-defend.")
        
        # Spawn OS Controller
        os_control = self.spawn_agent(AgentType.OS_CONTROL, mission.id,
                                      custom_caps=["monitor", "update", "harden", "audit", "optimize"])
        if os_control:
            mission.agents.append(os_control.id)
        
        # Spawn Defensive Core
        defender = self.spawn_agent(AgentType.DEFENSIVE, mission.id,
                                   custom_caps=["monitor", "detect", "block", "isolate", "learn"])
        if defender:
            mission.agents.append(defender.id)
        
        # Spawn Learning Agent
        learner = self.spawn_agent(AgentType.CUSTOM, mission.id,
                                  custom_caps=["analyze", "adapt", "create-strategy", "predict"])
        if learner:
            mission.agents.append(learner.id)
        
        mission.status = "active"
        
        # Start continuous monitoring loop
        self._autonomy_loop(mission)
        
        return mission
    
    def _autonomy_loop(self, mission: Mission):
        """Continuous autonomy loop."""
        cycle = 0
        while self.running and mission.status == "active":
            cycle += 1
            print(f"\n[BRAIN] Autonomy Cycle #{cycle}")
            
            # Self-check: are we healthy?
            self._health_check()
            
            # Check for threats
            threats = self._scan_for_threats()
            if threats:
                print(f"[BRAIN] ⚠️ {len(threats)} threats detected! Spawning defenders...")
                for threat in threats[:3]:  # Handle top 3
                    defender = self.spawn_agent(AgentType.DEFENSIVE, mission.id,
                                              custom_caps=["isolate", "analyze", threat.get("type", "block")])
                    if defender:
                        mission.agents.append(defender.id)
            
            # Self-improvement: learn from current state
            if cycle % 10 == 0:  # Every 10 cycles
                self._self_improve()
            
            # Report status
            active = len([a for a in self.agents.values() if a.status == AgentStatus.ACTIVE])
            busy = len([a for a in self.agents.values() if a.status == AgentStatus.BUSY])
            print(f"[BRAIN] Status: {active} active, {busy} busy, {len(self.learned_strategies)} strategies learned")
            
            time.sleep(30)  # 30-second cycles
    
    def _health_check(self):
        """Check system health and spawn repair agents if needed."""
        # Check disk space
        try:
            stat = os.statvfs("/")
            free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
            if free_gb < 5:
                print(f"[BRAIN] ⚠️ Low disk space ({free_gb:.1f}GB). Spawning cleanup agent...")
                cleanup = self.spawn_agent(AgentType.OS_CONTROL, "health",
                                          custom_caps=["cleanup", "log-rotate"])
                if cleanup:
                    # Execute cleanup
                    subprocess.run(["/usr/local/bin/aegisnova-wipe.sh", "--all"], 
                                capture_output=True, timeout=60)
        except Exception as e:
            pass
    
    def _scan_for_threats(self) -> List[Dict]:
        """Quick threat scan."""
        threats = []
        
        # Check for suspicious processes
        try:
            result = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=10)
            suspicious = ["nc", "ncat", "python -c", "bash -i", "/dev/tcp"]
            for line in result.stdout.split('\n'):
                for s in suspicious:
                    if s in line.lower():
                        threats.append({"type": "suspicious_process", "detail": line.strip()})
                        break
        except:
            pass
        
        # Check for failed logins
        try:
            result = subprocess.run(["grep", "Failed password", "/var/log/auth.log"],
                                capture_output=True, text=True, timeout=5)
            if result.stdout.count('\n') > 5:
                threats.append({"type": "brute_force", "count": result.stdout.count('\n')})
        except:
            pass
        
        return threats
    
    def _self_improve(self):
        """Analyze performance and create new strategies."""
        print("[BRAIN] 🧬 Running self-improvement cycle...")
        
        # Analyze successful strategies
        successful = [s for s in self.learned_strategies if s.get("success_rate", 0) > 0.7]
        
        if len(successful) > 5:
            # Create a composite strategy
            new_strategy = {
                "pattern": f"composite_v{len(self.learned_strategies)}",
                "components": [s["pattern"] for s in successful[:3]],
                "learned_at": datetime.utcnow().isoformat(),
                "uses": 0,
                "success_rate": 0.0
            }
            self.learned_strategies.append(new_strategy)
            self._save_learned()
            print(f"[BRAIN] ✨ New composite strategy created: {new_strategy['pattern']}")
    
    def _execute_recon(self, agent: Agent, target: str, scope: str):
        """Execute reconnaissance via the agent (non-blocking — runs in daemon thread)."""
        def _run():
            agent.status = AgentStatus.BUSY
            try:
                nmap_result = subprocess.run(
                    ["nmap", "-sV", "-T4", "--top-ports", "100", target],
                    capture_output=True, text=True, timeout=300
                )
                agent.results.append({
                    "tool": "nmap",
                    "output": nmap_result.stdout[:2000],
                    "success": nmap_result.returncode == 0
                })
                self.bus.publish("recon.results", {
                    "agent_id": agent.id,
                    "target": target,
                    "open_ports": self._parse_nmap_ports(nmap_result.stdout)
                })
            except Exception as e:
                agent.results.append({"tool": "nmap", "error": str(e)})
            finally:
                agent.status = AgentStatus.IDLE
                agent.last_activity = datetime.utcnow().isoformat()

        t = threading.Thread(target=_run, daemon=True, name=f"recon-{agent.id}")
        t.start()
    
    def _parse_nmap_ports(self, nmap_output: str) -> List[int]:
        """Parse open ports from nmap output."""
        import re
        ports = []
        for match in re.finditer(r'(\d+)/tcp\s+open', nmap_output):
            ports.append(int(match.group(1)))
        return ports
    
    def _execute_detection(self, agent: Agent, scope: str):
        """Execute detection routines."""
        agent.status = AgentStatus.BUSY
        
        # Run Suricata check
        try:
            result = subprocess.run(
                ["systemctl", "is-active", "suricata"],
                capture_output=True, text=True, timeout=10
            )
            if "inactive" in result.stdout.lower():
                # Spawn agent to start it
                self.spawn_agent(AgentType.OS_CONTROL, agent.mission_id,
                                custom_caps=["start-service", "suricata"])
        except:
            pass
        
        # Check audit logs
        try:
            result = subprocess.run(
                ["ausearch", "--start", "today", "-i"],
                capture_output=True, text=True, timeout=10
            )
            agent.results.append({
                "tool": "auditd",
                "alerts": len(result.stdout.split('\n')),
                "success": True
            })
        except:
            pass
        
        agent.status = AgentStatus.IDLE
    
    def _execute_hardening(self, agent: Agent):
        """Execute system hardening."""
        agent.status = AgentStatus.BUSY
        
        try:
            subprocess.run(["/usr/local/bin/harden-system.sh"],
                         capture_output=True, timeout=120)
            agent.results.append({"tool": "harden-system", "success": True})
        except Exception as e:
            agent.results.append({"tool": "harden-system", "error": str(e)})
        
        agent.status = AgentStatus.IDLE
    
    def status(self) -> Dict[str, Any]:
        """Get brain status."""
        active = [a for a in self.agents.values() if a.status == AgentStatus.ACTIVE]
        missions = [m for m in self.missions.values() if m.status == "active"]
        
        return {
            "brain_status": "running" if self.running else "stopped",
            "total_agents": len(self.agents),
            "active_agents": len(active),
            "active_missions": len(missions),
            "learned_strategies": len(self.learned_strategies),
            "uptime_cycles": "N/A",
            "agents": [
                {
                    "id": a.id,
                    "callsign": a.callsign,
                    "type": a.agent_type.value,
                    "status": a.status.value,
                    "voice": a.voice,
                    "specialty": a.specialty
                } for a in active
            ]
        }
    
    def show_codex(self):
        """Display the agent codex."""
        if CODEX_AVAILABLE:
            print("\n" + "="*70)
            print("  AEGIS BRAIN — AGENT CODEX")
            print("="*70)
            
            for category, agents in ALL_PERSONALITIES.items():
                print(f"\n  ⚔️  {category.upper()} AGENTS:")
                print("  " + "-"*50)
                for agent in agents:
                    print(f"    {agent['callsign']:<12} — {agent['name']}")
                    print(f"      Voice: {agent['voice']:<12} | Specialty: {agent['specialty']}")
                    print(f'      "{agent["quote"]}"')
                    print()
        else:
            print("[BRAIN] Agent Codex not available.")
    
    def destroy_agent(self, agent_id: str):
        """Destroy an agent."""
        if agent_id in self.agents:
            agent = self.agents[agent_id]
            agent.status = AgentStatus.DYING
            
            # Kill child agents recursively
            for child_id in agent.children:
                self.destroy_agent(child_id)
            
            if agent.pid:
                try:
                    os.kill(agent.pid, signal.SIGTERM)
                except:
                    pass
            
            agent.status = AgentStatus.DEAD
            
            self.bus.publish("brain.events", {
                "event": "agent_destroyed",
                "agent_id": agent_id
            })


def main():
    parser = argparse.ArgumentParser(description="AegisNova Brain — Master AI Orchestrator")
    parser.add_argument("--mode", choices=["autonomous", "command"], default="command",
                       help="Operation mode")
    parser.add_argument("--mission", help="Mission description")
    parser.add_argument("--target", help="Target for mission")
    parser.add_argument("--offensive", action="store_true", help="Launch offensive operation")
    parser.add_argument("--defensive", action="store_true", help="Launch defensive operation")
    parser.add_argument("--swarm-offense", action="store_true", help="Launch offensive swarm")
    parser.add_argument("--swarm-defense", action="store_true", help="Launch defensive swarm")
    parser.add_argument("--os-autopilot", action="store_true", help="Enable OS autopilot")
    parser.add_argument("--full-autonomy", action="store_true", help="Full system autonomy")
    parser.add_argument("--status", action="store_true", help="Show brain status")
    parser.add_argument("--max-agents", type=int, default=MAX_AGENTS, help="Max concurrent agents")
    
    args = parser.parse_args()
    
    brain = AegisBrain()
    brain.max_agents = args.max_agents
    
    if args.status:
        import pprint
        pprint.pprint(brain.status())
        return
    
    if args.full_autonomy:
        print("="*70)
        print("  🧠 AEGIS BRAIN — FULL AUTONOMY MODE")
        print("="*70)
        print("  The system will now self-operate, self-defend, and self-improve.")
        print("  Press Ctrl+C to regain manual control.")
        print("="*70)
        mission = brain.plan_full_autonomy()
        try:
            while brain.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[BRAIN] Manual override detected. Shutting down autonomy...")
            brain.running = False
        return
    
    if args.offensive or args.swarm_offense:
        if not args.target:
            print("Error: --target required for offensive operations")
            sys.exit(1)
        mission = brain.plan_offensive_operation(args.target)
        print(f"\nOffensive mission launched: {mission.id}")
        return
    
    if args.defensive or args.swarm_defense:
        mission = brain.plan_defensive_operation()
        print(f"\nDefensive mission launched: {mission.id}")
        return
    
    if args.os_autopilot:
        mission = brain.create_mission(
            MissionType.OS_AUTOMATION,
            "OS Autopilot Mode",
            objectives=["monitor", "maintain", "optimize"]
        )
        os_agent = brain.spawn_agent(AgentType.OS_CONTROL, mission.id,
                                     custom_caps=["full-control", "monitor", "optimize"])
        if os_agent:
            mission.agents.append(os_agent.id)
        mission.status = "active"
        print(f"\nOS Autopilot activated: {mission.id}")
        print("The system will self-monitor and self-maintain.")
        return
    
    if args.mission:
        mission = brain.create_mission(
            MissionType.CUSTOM if not args.offensive else MissionType.OFFENSIVE_OPERATION,
            args.mission,
            target=args.target
        )
        print(f"\nCustom mission created: {mission.id}")
        print(f"Description: {args.mission}")
        if args.target:
            print(f"Target: {args.target}")
        return
    
    # Interactive mode
    print("="*70)
    print("  🧠 AEGIS BRAIN — Interactive Mode")
    print("="*70)
    print("\nAvailable commands:")
    print("  offense <target>  - Launch offensive operation")
    print("  defense           - Launch defensive operation")
    print("  autonomy          - Enable full autonomy")
    print("  autopilot         - OS autopilot mode")
    print("  status            - Show brain status")
    print("  codex             - Show agent codex (names & personalities)")
    print("  spawn <type>      - Spawn agent type")
    print("  destroy <id>      - Destroy agent")
    print("  agents            - List agents")
    print("  missions          - List missions")
    print("  learn             - Force learning cycle")
    print("  quit              - Exit")
    print("="*70)
    
    while brain.running:
        try:
            cmd = input("\n[BRAIN] > ").strip().split()
            if not cmd:
                continue
            
            if cmd[0] == "quit":
                break
            elif cmd[0] == "status":
                import pprint
                pprint.pprint(brain.status())
            elif cmd[0] == "offense" and len(cmd) > 1:
                brain.plan_offensive_operation(cmd[1])
            elif cmd[0] == "defense":
                brain.plan_defensive_operation()
            elif cmd[0] == "autonomy":
                brain.plan_full_autonomy()
            elif cmd[0] == "autopilot":
                print("Use --os-autopilot flag")
            elif cmd[0] == "agents":
                print(f"\n  {'ID':<15} {'CALLSIGN':<12} {'TYPE':<12} {'STATUS':<10} {'VOICE'}")
                print("  " + "-"*70)
                for aid, agent in brain.agents.items():
                    print(f"  {aid:<15} {agent.callsign:<12} {agent.agent_type.value:<12} {agent.status.value:<10} {agent.voice}")
                print()
            elif cmd[0] == "codex":
                brain.show_codex()
            elif cmd[0] == "missions":
                for mid, mission in brain.missions.items():
                    print(f"  {mid}: {mission.description} [{mission.status}]")
            elif cmd[0] == "spawn" and len(cmd) > 1:
                atype = AgentType(cmd[1]) if cmd[1] in [t.value for t in AgentType] else AgentType.CUSTOM
                agent = brain.spawn_agent(atype, "manual")
                if agent:
                    print(f"  Spawned: {agent.id}")
            elif cmd[0] == "destroy" and len(cmd) > 1:
                brain.destroy_agent(cmd[1])
                print(f"  Destroyed: {cmd[1]}")
            elif cmd[0] == "learn":
                brain._self_improve()
            else:
                print(f"  Unknown command: {cmd[0]}")
        
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"  Error: {e}")
    
    print("\n[BRAIN] Shutting down...")
    brain._shutdown(0, None)


if __name__ == "__main__":
    main()
