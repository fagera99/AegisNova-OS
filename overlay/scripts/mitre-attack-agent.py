#!/usr/bin/env python3
"""
AegisNova OS — MITRE ATT&CK Mapping Agent
===========================================
Maps security events, tools, and techniques to MITRE ATT&CK framework.
Provides:
- Technique lookup by ID or name
- Automatic mapping of tool output to ATT&CK techniques
- Report generation with MITRE mappings
- TTP (Tactics, Techniques, Procedures) extraction

Usage:
    python3 mitre-attack-agent.py --lookup T1003
    python3 mitre-attack-agent.py --map-tool bloodhound
    python3 mitre-attack-agent.py --analyze-log /var/log/auth.log
    python3 mitre-attack-agent.py --generate-report --output report.json
"""

import json
import os
import re
import sys
import argparse
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

# ── Configuration ──
ATTACK_DATA_DIR = "/opt/aegisnova/attack-data"
ATTACK_VERSION = "v14.1"
ATTACK_URL = f"https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"

# ── Technique Database (subset for offline use) ──
TECHNIQUES_DB = {
    "T1003": {
        "name": "OS Credential Dumping",
        "tactics": ["Credential Access"],
        "description": "Adversaries may dump credentials to obtain account login and credential material.",
        "platforms": ["Windows", "macOS", "Linux"],
        "subtechniques": ["T1003.001", "T1003.002", "T1003.004", "T1003.005", "T1003.006"],
    },
    "T1003.001": {
        "name": "OS Credential Dumping: LSASS Memory",
        "tactics": ["Credential Access"],
        "description": "Adversaries may dump credentials from LSASS memory.",
        "platforms": ["Windows"],
        "subtechniques": [],
    },
    "T1059": {
        "name": "Command and Scripting Interpreter",
        "tactics": ["Execution"],
        "description": "Adversaries may abuse command and script interpreters to execute commands, scripts, or binaries.",
        "platforms": ["Windows", "macOS", "Linux"],
        "subtechniques": ["T1059.001", "T1059.002", "T1059.003", "T1059.004", "T1059.005", "T1059.006", "T1059.007"],
    },
    "T1059.001": {
        "name": "Command and Scripting Interpreter: PowerShell",
        "tactics": ["Execution"],
        "description": "Adversaries may abuse PowerShell commands and scripts for execution.",
        "platforms": ["Windows"],
        "subtechniques": [],
    },
    "T1059.003": {
        "name": "Command and Scripting Interpreter: Windows Command Shell",
        "tactics": ["Execution"],
        "description": "Adversaries may abuse cmd.exe to execute commands.",
        "platforms": ["Windows"],
        "subtechniques": [],
    },
    "T1059.006": {
        "name": "Command and Scripting Interpreter: Python",
        "tactics": ["Execution"],
        "description": "Adversaries may abuse Python commands and scripts for execution.",
        "platforms": ["Windows", "macOS", "Linux"],
        "subtechniques": [],
    },
    "T1087": {
        "name": "Account Discovery",
        "tactics": ["Discovery"],
        "description": "Adversaries may attempt to get a listing of accounts on a system or within an environment.",
        "platforms": ["Windows", "macOS", "Linux"],
        "subtechniques": ["T1087.001", "T1087.002", "T1087.003", "T1087.004"],
    },
    "T1087.002": {
        "name": "Account Discovery: Domain Account",
        "tactics": ["Discovery"],
        "description": "Adversaries may attempt to get a listing of domain accounts.",
        "platforms": ["Windows"],
        "subtechniques": [],
    },
    "T1136": {
        "name": "Create Account",
        "tactics": ["Persistence"],
        "description": "Adversaries may create an account to maintain access to victim systems.",
        "platforms": ["Windows", "macOS", "Linux"],
        "subtechniques": ["T1136.001", "T1136.002", "T1136.003"],
    },
    "T1203": {
        "name": "Exploitation for Client Execution",
        "tactics": ["Execution"],
        "description": "Adversaries may exploit software vulnerabilities in client applications to execute code.",
        "platforms": ["Windows", "macOS", "Linux"],
        "subtechniques": [],
    },
    "T1210": {
        "name": "Exploitation of Remote Services",
        "tactics": ["Lateral Movement"],
        "description": "Adversaries may exploit remote services to gain unauthorized access to internal systems.",
        "platforms": ["Windows", "macOS", "Linux"],
        "subtechniques": [],
    },
    "T1548": {
        "name": "Abuse Elevation Control Mechanism",
        "tactics": ["Privilege Escalation"],
        "description": "Adversaries may circumvent mechanisms designed to control elevation privileges.",
        "platforms": ["Windows", "macOS", "Linux"],
        "subtechniques": ["T1548.001", "T1548.002", "T1548.003", "T1548.004"],
    },
    "T1550": {
        "name": "Use Alternate Authentication Material",
        "tactics": ["Defense Evasion", "Lateral Movement"],
        "description": "Adversaries may use alternate authentication material to bypass system access controls.",
        "platforms": ["Windows", "macOS", "Linux"],
        "subtechniques": ["T1550.001", "T1550.002", "T1550.003", "T1550.004"],
    },
    "T1550.002": {
        "name": "Use Alternate Authentication Material: Pass the Hash",
        "tactics": ["Lateral Movement"],
        "description": "Adversaries may 'pass the hash' using stolen password hashes to move laterally.",
        "platforms": ["Windows"],
        "subtechniques": [],
    },
    "T1550.003": {
        "name": "Use Alternate Authentication Material: Pass the Ticket",
        "tactics": ["Lateral Movement"],
        "description": "Adversaries may 'pass the ticket' using stolen Kerberos tickets to move laterally.",
        "platforms": ["Windows"],
        "subtechniques": [],
    },
    "T1558": {
        "name": "Steal or Forge Kerberos Tickets",
        "tactics": ["Credential Access"],
        "description": "Adversaries may steal or forge Kerberos tickets to bypass access controls.",
        "platforms": ["Windows"],
        "subtechniques": ["T1558.001", "T1558.002", "T1558.003", "T1558.004"],
    },
    "T1558.003": {
        "name": "Steal or Forge Kerberos Tickets: Kerberoasting",
        "tactics": ["Credential Access"],
        "description": "Adversaries may abuse a valid Kerberos ticket-granting ticket (TGT) to request service tickets.",
        "platforms": ["Windows"],
        "subtechniques": [],
    },
    "T1567": {
        "name": "Exfiltration Over Web Service",
        "tactics": ["Exfiltration"],
        "description": "Adversaries may use an existing, legitimate external Web service to exfiltrate data.",
        "platforms": ["Windows", "macOS", "Linux"],
        "subtechniques": ["T1567.001", "T1567.002", "T1567.003", "T1567.004"],
    },
    "T1574": {
        "name": "Hijack Execution Flow",
        "tactics": ["Persistence", "Privilege Escalation"],
        "description": "Adversaries may execute their own malicious payloads by hijacking the execution flow.",
        "platforms": ["Windows", "macOS", "Linux"],
        "subtechniques": ["T1574.001", "T1574.002", "T1574.004", "T1574.006", "T1574.007", "T1574.008", "T1574.009", "T1574.010", "T1574.011", "T1574.012", "T1574.013"],
    },
    "T1071": {
        "name": "Application Layer Protocol",
        "tactics": ["Command and Control"],
        "description": "Adversaries may communicate using OSI application layer protocols to avoid detection.",
        "platforms": ["Windows", "macOS", "Linux"],
        "subtechniques": ["T1071.001", "T1071.002", "T1071.003", "T1071.004"],
    },
    "T1071.001": {
        "name": "Application Layer Protocol: Web Protocols",
        "tactics": ["Command and Control"],
        "description": "Adversaries may communicate using application layer protocols associated with web traffic.",
        "platforms": ["Windows", "macOS", "Linux"],
        "subtechniques": [],
    },
}

# Tool to Technique Mapping
TOOL_TECHNIQUES = {
    "mimikatz": ["T1003", "T1003.001", "T1550.002", "T1550.003", "T1558.003"],
    "bloodhound": ["T1087", "T1087.002", "T1018", "T1482"],
    "hashcat": ["T1003", "T1110", "T1552"],
    "john": ["T1003", "T1110"],
    "responder": ["T1557", "T1557.001", "T1040"],
    "metasploit": ["T1203", "T1210", "T1059", "T1059.001", "T1059.003"],
    "empire": ["T1059", "T1059.001", "T1071", "T1071.001"],
    "sliver": ["T1071", "T1071.001", "T1059"],
    "sqlmap": ["T1190", "T1210"],
    "nmap": ["T1046", "T1018", "T1040"],
    "amass": ["T1590", "T1590.001", "T1590.002"],
    "masscan": ["T1046"],
    "nuclei": ["T1190", "T1210"],
    "burpsuite": ["T1190", "T1210"],
    "zaproxy": ["T1190", "T1210"],
    "aircrack-ng": ["T1200", "T1110"],
    "bettercap": ["T1040", "T1557"],
    "impacket": ["T1550.002", "T1550.003", "T1021"],
    "crackmapexec": ["T1021", "T1077", "T1110"],
    "evil-winrm": ["T1021", "T1021.006"],
    "pwncat": ["T1059", "T1059.003"],
    "commix": ["T1059", "T1059.006"],
    "beef-xss": ["T1189", "T1059.007"],
    "feroxbuster": ["T1083", "T1135"],
    "gobuster": ["T1083", "T1135"],
    "ffuf": ["T1083", "T1135"],
    "nikto": ["T1190"],
    "hydra": ["T1110", "T1110.001"],
    "medusa": ["T1110"],
    "wireshark": ["T1040", "T1046"],
    "tcpdump": ["T1040", "T1046"],
    "suricata": ["T1040", "T1071", "T1190"],
    "zeek": ["T1040", "T1071", "T1071.001"],
    "wazuh": ["T1005", "T1040", "T1056"],
    "osquery": ["T1082", "T1083", "T1049"],
    "volatility3": ["T1003", "T1004", "T1005"],
    "autopsy": ["T1005", "T1036", "T1070"],
    "yara": ["T1027", "T1036", "T1055"],
    "lynis": ["T1070", "T1082", "T1049"],
    "trivy": ["T1195", "T1195.001"],
    "openvas": ["T1046", "T1190"],
    "clamav": ["T1027", "T1036", "T1204"],
    "rkhunter": ["T1014", "T1547"],
    "chkrootkit": ["T1014"],
    "auditd": ["T1005", "T1070", "T1562"],
    "bpftrace": ["T1056", "T1070", "T1562.001"],
    "sysmon-for-linux": ["T1001", "T1056", "T1070"],
}

# ── Data Classes ──
@dataclass
class TechniqueMapping:
    technique_id: str
    technique_name: str
    tactics: List[str]
    tools: List[str]
    confidence: str  # high, medium, low
    context: str

@dataclass
class AttackReport:
    timestamp: str
    source: str
    mappings: List[TechniqueMapping]
    summary: str

# ── Core Functions ──
class ATTACKMapper:
    """Maps security events and tools to MITRE ATT&CK techniques."""
    
    def __init__(self):
        self.techniques = TECHNIQUES_DB
        self.tool_map = TOOL_TECHNIQUES
    
    def lookup_technique(self, technique_id: str) -> Optional[Dict[str, Any]]:
        """Look up a technique by ID."""
        return self.techniques.get(technique_id.upper())
    
    def search_techniques(self, keyword: str) -> List[Dict[str, Any]]:
        """Search techniques by keyword."""
        results = []
        keyword_lower = keyword.lower()
        
        for tid, data in self.techniques.items():
            if (keyword_lower in tid.lower() or
                keyword_lower in data.get("name", "").lower() or
                keyword_lower in data.get("description", "").lower()):
                results.append({"id": tid, **data})
        
        return results
    
    def map_tool(self, tool_name: str) -> List[TechniqueMapping]:
        """Map a tool to its ATT&CK techniques."""
        mappings = []
        tool_lower = tool_name.lower()
        
        for tool, techniques in self.tool_map.items():
            if tool_lower == tool or tool_lower in tool:
                for tid in techniques:
                    tech_data = self.lookup_technique(tid)
                    if tech_data:
                        mappings.append(TechniqueMapping(
                            technique_id=tid,
                            technique_name=tech_data["name"],
                            tactics=tech_data["tactics"],
                            tools=[tool],
                            confidence="high",
                            context=f"Tool '{tool_name}' is commonly associated with this technique"
                        ))
        
        return mappings
    
    def analyze_log(self, log_file: str) -> List[TechniqueMapping]:
        """Analyze a log file for ATT&CK technique indicators."""
        mappings = []
        
        if not os.path.exists(log_file):
            print(f"Log file not found: {log_file}")
            return mappings
        
        with open(log_file, 'r', errors='ignore') as f:
            content = f.read().lower()
        
        # Pattern mappings for log analysis
        patterns = {
            "T1003": ["credential", "dump", "mimikatz", "lsa", "password"],
            "T1059": ["powershell", "cmd.exe", "bash", "python", "script"],
            "T1071": ["http", "https", "dns", "beacon", "callback"],
            "T1087": ["user", "account", "domain account", "enum"],
            "T1136": ["useradd", "net user", "create account"],
            "T1203": ["exploit", "shellcode", "buffer overflow"],
            "T1550": ["pass the hash", "pass the ticket", "pth", "ptt"],
            "T1558": ["kerberoast", "asrep", "tgt", "tgs"],
            "T1567": ["upload", "exfil", "cloud", "dropbox", "drive"],
            "T1574": ["dll", "hijack", "proxy", "path"],
        }
        
        for tid, keywords in patterns.items():
            matches = sum(1 for kw in keywords if kw in content)
            if matches >= 2:
                tech_data = self.lookup_technique(tid)
                if tech_data:
                    mappings.append(TechniqueMapping(
                        technique_id=tid,
                        technique_name=tech_data["name"],
                        tactics=tech_data["tactics"],
                        tools=[],
                        confidence="medium" if matches < 4 else "high",
                        context=f"Detected {matches} indicators in log file"
                    ))
        
        return mappings
    
    def generate_report(self, mappings: List[TechniqueMapping], source: str = "unknown") -> Dict[str, Any]:
        """Generate a structured ATT&CK report."""
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "source": source,
            "aegisnova_version": "1.0.0",
            "mitre_attack_version": ATTACK_VERSION,
            "summary": {
                "total_techniques": len(mappings),
                "unique_tactics": list(set(t for m in mappings for t in m.tactics)),
                "high_confidence": len([m for m in mappings if m.confidence == "high"]),
                "medium_confidence": len([m for m in mappings if m.confidence == "medium"]),
                "low_confidence": len([m for m in mappings if m.confidence == "low"]),
            },
            "techniques": [asdict(m) for m in mappings],
            "tactics_breakdown": self._tactics_breakdown(mappings),
        }
        
        return report
    
    def _tactics_breakdown(self, mappings: List[TechniqueMapping]) -> Dict[str, List[str]]:
        """Group techniques by tactics."""
        breakdown = {}
        for mapping in mappings:
            for tactic in mapping.tactics:
                if tactic not in breakdown:
                    breakdown[tactic] = []
                breakdown[tactic].append(mapping.technique_id)
        return breakdown
    
    def download_attack_data(self) -> bool:
        """Download latest ATT&CK data from MITRE."""
        os.makedirs(ATTACK_DATA_DIR, exist_ok=True)
        
        try:
            import urllib.request
            print(f"Downloading MITRE ATT&CK data from {ATTACK_URL} ...")
            urllib.request.urlretrieve(
                ATTACK_URL,
                f"{ATTACK_DATA_DIR}/enterprise-attack.json"
            )
            print("ATT&CK data downloaded successfully.")
            return True
        except Exception as e:
            print(f"Failed to download ATT&CK data: {e}")
            print("Using built-in technique database instead.")
            return False


# ── CLI Interface ──
def main():
    parser = argparse.ArgumentParser(
        description="AegisNova MITRE ATT&CK Mapping Agent"
    )
    parser.add_argument("--lookup", help="Look up technique by ID")
    parser.add_argument("--search", help="Search techniques by keyword")
    parser.add_argument("--map-tool", help="Map a tool to ATT&CK techniques")
    parser.add_argument("--analyze-log", help="Analyze log file for techniques")
    parser.add_argument("--generate-report", action="store_true", help="Generate JSON report")
    parser.add_argument("--output", "-o", default="-", help="Output file (default: stdout)")
    parser.add_argument("--download-data", action="store_true", help="Download latest ATT&CK data")
    
    args = parser.parse_args()
    
    mapper = ATTACKMapper()
    
    if args.download_data:
        mapper.download_attack_data()
        return
    
    mappings = []
    
    if args.lookup:
        technique = mapper.lookup_technique(args.lookup)
        if technique:
            print(f"\n{'='*60}")
            print(f"  Technique: {args.lookup.upper()}")
            print(f"  Name: {technique['name']}")
            print(f"  Tactics: {', '.join(technique['tactics'])}")
            print(f"  Platforms: {', '.join(technique['platforms'])}")
            print(f"\n  Description:")
            print(f"    {technique['description']}")
            if technique.get("subtechniques"):
                print(f"\n  Sub-techniques: {', '.join(technique['subtechniques'])}")
            print(f"{'='*60}\n")
        else:
            print(f"Technique {args.lookup} not found in database.")
        return
    
    if args.search:
        results = mapper.search_techniques(args.search)
        print(f"\nSearch results for '{args.search}':")
        print("-" * 60)
        for result in results:
            print(f"  {result['id']}: {result['name']}")
            print(f"    Tactics: {', '.join(result['tactics'])}")
        print()
        return
    
    if args.map_tool:
        mappings = mapper.map_tool(args.map_tool)
        source = f"tool:{args.map_tool}"
    
    if args.analyze_log:
        log_mappings = mapper.analyze_log(args.analyze_log)
        mappings.extend(log_mappings)
        source = f"log:{args.analyze_log}"
    
    if args.generate_report or mappings:
        report = mapper.generate_report(mappings, source=getattr(args, 'map_tool', 'analysis'))
        
        output = json.dumps(report, indent=2, ensure_ascii=False)
        
        if args.output == "-":
            print(output)
        else:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"Report saved to: {args.output}")
    
    if not any([args.lookup, args.search, args.map_tool, args.analyze_log, args.download_data]):
        parser.print_help()
        print("\n\nExamples:")
        print("  mitre-attack-agent.py --lookup T1003")
        print("  mitre-attack-agent.py --map-tool bloodhound")
        print("  mitre-attack-agent.py --analyze-log /var/log/auth.log --output report.json")


if __name__ == "__main__":
    main()
