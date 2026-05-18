#!/usr/bin/env python3
"""
AegisNova OS — Incident Response Playbook Automation
======================================================
Automated incident response playbooks for common security scenarios:
- Malware detection response
- Credential compromise response
- Lateral movement detection
- Data exfiltration response
- Ransomware response
- Insider threat detection

Each playbook provides:
- Automated containment steps
- Evidence collection
- Notification/alerting
- Remediation actions
- Forensic preservation

Usage:
    python3 ir-playbook.py --playbook malware --target host1
    python3 ir-playbook.py --playbook credentials --target user@domain
    python3 ir-playbook.py --list
    python3 ir-playbook.py --playbook ransomware --dry-run
"""

import json
import os
import sys
import subprocess
import argparse
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

# ── Configuration ──
IR_DIR = "/var/log/aegisnova/incident-response"
EVIDENCE_DIR = "/var/log/aegisnova/evidence"
ALERT_CONFIG = "/etc/aegisnova/ir-alerts.conf"

class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class IRAction:
    step: int
    name: str
    command: str
    description: str
    requires_root: bool
    destructive: bool
    evidence_collected: bool

@dataclass
class IRPlaybook:
    name: str
    description: str
    severity: Severity
    triggers: List[str]
    actions: List[IRAction]
    notification_message: str

# ── Playbook Definitions ──

PLAYBOOKS = {
    "malware": IRPlaybook(
        name="Malware Detection and Response",
        description="Response playbook for suspected malware infection",
        severity=Severity.HIGH,
        triggers=["yara match", "clamav alert", "suspicious process", "known bad hash"],
        actions=[
            IRAction(1, "Isolate Network", "nft insert rule inet filter input drop", 
                    "Immediately isolate host from network", True, False, False),
            IRAction(2, "Preserve Process List", "ps aux > /var/log/aegisnova/evidence/processes-$(date +%s).log",
                    "Capture current process list", False, False, True),
            IRAction(3, "Preserve Network Connections", "ss -tulpn > /var/log/aegisnova/evidence/network-$(date +%s).log",
                    "Capture active network connections", False, False, True),
            IRAction(4, "Memory Dump", "dd if=/dev/mem of=/var/log/aegisnova/evidence/memdump-$(date +%s).bin bs=1M count=256",
                    "Capture memory dump (if possible)", True, False, True),
            IRAction(5, "Kill Suspicious Process", "kill -9 {pid}",
                    "Terminate identified malicious process", True, True, False),
            IRAction(6, "YARA Full Scan", "yara -r /opt/yara-rules/all.yara / 2>/dev/null > /var/log/aegisnova/evidence/yara-$(date +%s).log",
                    "Run full YARA scan", False, False, True),
            IRAction(7, "Collect File Hashes", "find /tmp /var/tmp -type f -exec sha256sum {} \; > /var/log/aegisnova/evidence/hashes-$(date +%s).log",
                    "Collect hashes of temporary files", False, False, True),
            IRAction(8, "Notify Team", "echo 'Malware incident detected on $(hostname)'",
                    "Send alert notification", False, False, False),
        ],
        notification_message="MALWARE INCIDENT: Host isolation initiated. Immediate review required."
    ),
    
    "credentials": IRPlaybook(
        name="Credential Compromise Response",
        description="Response playbook for suspected credential compromise",
        severity=Severity.CRITICAL,
        triggers=["kerberoasting detected", "pass-the-hash", "failed logins spike", "impossible travel"],
        actions=[
            IRAction(1, "Disable Compromised Account", "passwd -l {username}",
                    "Lock compromised user account immediately", True, True, False),
            IRAction(2, "Revoke Active Sessions", "pkill -u {username}",
                    "Kill all active sessions for user", True, True, False),
            IRAction(3, "Force Password Reset", "passwd -e {username}",
                    "Expire password to force reset on next login", True, False, False),
            IRAction(4, "Audit Recent Logins", "last -a {username} > /var/log/aegisnova/evidence/logins-$(date +%s).log",
                    "Capture login history for affected user", False, False, True),
            IRAction(5, "Check Sudoers", "cat /etc/sudoers /etc/sudoers.d/* > /var/log/aegisnova/evidence/sudoers-$(date +%s).log",
                    "Preserve sudoers configuration", False, False, True),
            IRAction(6, "Audit SSH Keys", "find /home -name authorized_keys -exec cat {} \; > /var/log/aegisnova/evidence/sshkeys-$(date +%s).log",
                    "Collect all authorized SSH keys", False, False, True),
            IRAction(7, "Generate New Keytab", "ktutil",
                    "Generate new Kerberos keytab if needed", True, False, False),
            IRAction(8, "Notify Security Team", "echo 'Credential compromise detected for {username}'",
                    "Send critical alert", False, False, False),
        ],
        notification_message="CRITICAL: Credential compromise detected. Account locked and sessions terminated."
    ),
    
    "lateral_movement": IRPlaybook(
        name="Lateral Movement Detection Response",
        description="Response for detected lateral movement attempts",
        severity=Severity.HIGH,
        triggers=["smb exec", "wmi exec", "ps exec", "remote service creation", "psexec artifacts"],
        actions=[
            IRAction(1, "Block SMB", "nft add rule inet filter input tcp dport 445 drop",
                    "Block inbound SMB connections", True, False, False),
            IRAction(2, "Audit Shares", "smbstatus -S > /var/log/aegisnova/evidence/shares-$(date +%s).log",
                    "Enumerate active SMB shares", False, False, True),
            IRAction(3, "Check Running Services", "systemctl list-units --type=service --state=running > /var/log/aegisnova/evidence/services-$(date +%s).log",
                    "List all running services", False, False, True),
            IRAction(4, "Audit Scheduled Tasks", "find /etc/cron* -type f -exec ls -la {} \; > /var/log/aegisnova/evidence/crons-$(date +%s).log",
                    "Collect all cron jobs", False, False, True),
            IRAction(5, "Check Registry Run Keys", "echo 'Windows only - check HKLM\\Run and HKCU\\Run'",
                    "Note: Run keys check (Windows systems)", False, False, False),
            IRAction(6, "Network Segmentation", "nft add rule inet filter forward drop",
                    "Block all forwarding traffic", True, False, False),
            IRAction(7, "Preserve Evidence", "tar czf /var/log/aegisnova/evidence/evidence-$(date +%s).tar.gz /var/log",
                    "Compress log files for forensic analysis", False, False, True),
        ],
        notification_message="LATERAL MOVEMENT: Network segmentation applied. SMB blocked. Immediate investigation required."
    ),
    
    "exfiltration": IRPlaybook(
        name="Data Exfiltration Response",
        description="Response for suspected data exfiltration",
        severity=Severity.CRITICAL,
        triggers=["large outbound transfer", "unusual DNS queries", "cloud upload spike", "compressed archive creation"],
        actions=[
            IRAction(1, "Block Outbound", "nft add rule inet filter output drop",
                    "Block all outbound traffic immediately", True, False, False),
            IRAction(2, "Capture Netstat", "ss -i > /var/log/aegisnova/evidence/netstat-$(date +%s).log",
                    "Capture detailed network statistics", False, False, True),
            IRAction(3, "Check Recent Archives", "find / -name '*.tar.gz' -o -name '*.zip' -mtime -1 > /var/log/aegisnova/evidence/archives-$(date +%s).log",
                    "Find recently created archives", False, False, True),
            IRAction(4, "Audit Large Files", "find /home /tmp /var -size +100M -type f > /var/log/aegisnova/evidence/largefiles-$(date +%s).log",
                    "Find files larger than 100MB", False, False, True),
            IRAction(5, "Preserve Firewall Logs", "cat /var/log/nftables.log > /var/log/aegisnova/evidence/firewall-$(date +%s).log",
                    "Copy firewall logs", False, False, True),
            IRAction(6, "Memory Analysis", "echo 'Consider running volatility3 for memory analysis'",
                    "Flag for memory analysis", False, False, False),
        ],
        notification_message="CRITICAL: Data exfiltration suspected. Outbound traffic blocked. Immediate response required."
    ),
    
    "ransomware": IRPlaybook(
        name="Ransomware Response",
        description="Emergency response for ransomware infection",
        severity=Severity.CRITICAL,
        triggers=["file extension changed", "ransom note found", "mass file encryption", "shadow copy deletion"],
        actions=[
            IRAction(1, "EMERGENCY ISOLATION", "nft flush ruleset; nft add rule inet filter input drop; nft add rule inet filter output drop",
                    "COMPLETE NETWORK ISOLATION", True, False, False),
            IRAction(2, "Preserve Ransom Note", "find / -name '*README*' -o -name '*DECRYPT*' -o -name '*RECOVER*' > /var/log/aegisnova/evidence/ransomnotes-$(date +%s).log",
                    "Find and log all ransom notes", False, False, True),
            IRAction(3, "Check Backup Status", "ls -la /backup /var/backups 2>/dev/null > /var/log/aegisnova/evidence/backups-$(date +%s).log",
                    "Check if backups are available", False, False, True),
            IRAction(4, "Preserve Process List", "ps aux > /var/log/aegisnova/evidence/processes-$(date +%s).log",
                    "Capture all running processes", False, False, True),
            IRAction(5, "Memory Dump URGENT", "dd if=/dev/mem of=/var/log/aegisnova/evidence/memdump-$(date +%s).bin 2>/dev/null || echo 'Memory dump failed - continue with disk forensics'",
                    "Attempt memory dump before encryption spreads", True, False, True),
            IRAction(6, "Identify Encrypted Files", "find /home /var /opt -name '*.encrypted' -o -name '*.locked' -o -name '*.crypt' > /var/log/aegisnova/evidence/encrypted-$(date +%s).log",
                    "Find encrypted files for recovery assessment", False, False, True),
            IRAction(7, "DO NOT PAY RANSOM", "echo 'DO NOT PAY RANSOM - Contact law enforcement and use backups'",
                    "Critical advisory", False, False, False),
        ],
        notification_message="RANSOMWARE EMERGENCY: Full isolation applied. DO NOT PAY. Use backups. Law enforcement contact advised."
    ),
    
    "insider_threat": IRPlaybook(
        name="Insider Threat Response",
        description="Response for suspected insider threat activity",
        severity=Severity.HIGH,
        triggers=["unusual after-hours access", "bulk file download", "privilege escalation attempt", "sensitive data access"],
        actions=[
            IRAction(1, "Enable Enhanced Auditing", "auditctl -w /etc/shadow -p wa -k identity-file-changes",
                    "Enable file access auditing", True, False, False),
            IRAction(2, "User Activity Log", "last -f /var/log/wtmp > /var/log/aegisnova/evidence/activity-$(date +%s).log",
                    "Capture complete login history", False, False, True),
            IRAction(3, "Command History", "find /home -name '.bash_history' -exec cat {} \; > /var/log/aegisnova/evidence/history-$(date +%s).log",
                    "Collect all shell history", False, False, True),
            IRAction(4, "File Access Log", "ausearch -k identity-file-changes > /var/log/aegisnova/evidence/audit-$(date +%s).log",
                    "Query audit logs", False, False, True),
            IRAction(5, "Restrict Privileges", "usermod -G users {username}",
                    "Remove user from all groups except users", True, True, False),
            IRAction(6, "Monitor Network", "ss -tulpn > /var/log/aegisnova/evidence/connections-$(date +%s).log",
                    "Capture all network connections", False, False, True),
        ],
        notification_message="INSIDER THREAT: Enhanced monitoring active. User privileges restricted. Investigation initiated."
    ),
}

# ── Core Functions ──
class IncidentResponder:
    """Automated incident response handler."""
    
    def __init__(self):
        self.playbooks = PLAYBOOKS
        os.makedirs(IR_DIR, exist_ok=True)
        os.makedirs(EVIDENCE_DIR, exist_ok=True)
    
    def list_playbooks(self) -> None:
        """List all available playbooks."""
        print("\n" + "="*70)
        print("Available Incident Response Playbooks")
        print("="*70)
        
        for name, playbook in self.playbooks.items():
            print(f"\n{name.upper()}")
            print(f"  Description: {playbook.description}")
            print(f"  Severity: {playbook.severity.value.upper()}")
            print(f"  Triggers: {', '.join(playbook.triggers)}")
            print(f"  Actions: {len(playbook.actions)}")
        
        print("\n" + "="*70)
    
    def execute_playbook(self, playbook_name: str, target: str = "", dry_run: bool = False) -> Dict[str, Any]:
        """Execute an incident response playbook."""
        playbook = self.playbooks.get(playbook_name)
        
        if not playbook:
            print(f"Playbook '{playbook_name}' not found.")
            return {"success": False, "error": "Playbook not found"}
        
        incident_id = f"IR-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        log_file = f"{IR_DIR}/{incident_id}.log"
        
        print(f"\n{'='*70}")
        print(f"INCIDENT RESPONSE INITIATED")
        print(f"{'='*70}")
        print(f"Incident ID: {incident_id}")
        print(f"Playbook: {playbook.name}")
        print(f"Severity: {playbook.severity.value.upper()}")
        print(f"Target: {target or 'N/A'}")
        print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
        print(f"{'='*70}\n")
        
        execution_log = {
            "incident_id": incident_id,
            "playbook": playbook_name,
            "timestamp": datetime.utcnow().isoformat(),
            "target": target,
            "dry_run": dry_run,
            "severity": playbook.severity.value,
            "actions_executed": [],
            "evidence_collected": [],
            "errors": []
        }
        
        for action in playbook.actions:
            print(f"[{action.step}/{len(playbook.actions)}] {action.name}")
            print(f"  Description: {action.description}")
            
            if dry_run:
                print(f"  [DRY RUN] Would execute: {action.command}")
                print(f"  [DRY RUN] Root required: {action.requires_root}")
                print(f"  [DRY RUN] Destructive: {action.destructive}")
                print()
                continue
            
            # Replace placeholders
            command = action.command
            if target:
                command = command.replace("{username}", target)
                command = command.replace("{pid}", target)
                command = command.replace("{hostname}", target)
            
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                status = "SUCCESS" if result.returncode == 0 else "FAILED"
                print(f"  Status: {status}")
                
                if result.stdout:
                    print(f"  Output: {result.stdout[:200]}")
                
                execution_log["actions_executed"].append({
                    "step": action.step,
                    "name": action.name,
                    "status": status,
                    "command": command
                })
                
                if action.evidence_collected:
                    execution_log["evidence_collected"].append(action.name)
                
            except Exception as e:
                print(f"  Error: {e}")
                execution_log["errors"].append({
                    "step": action.step,
                    "name": action.name,
                    "error": str(e)
                })
            
            print()
        
        # Save execution log
        with open(log_file, 'w') as f:
            json.dump(execution_log, f, indent=2)
        
        print(f"{'='*70}")
        print(f"INCIDENT RESPONSE COMPLETE")
        print(f"{'='*70}")
        print(f"Log saved: {log_file}")
        print(f"Evidence: {EVIDENCE_DIR}/")
        print(f"Actions: {len(execution_log['actions_executed'])}")
        print(f"Evidence collected: {len(execution_log['evidence_collected'])}")
        print(f"Errors: {len(execution_log['errors'])}")
        print(f"\n{playbook.notification_message}")
        print(f"{'='*70}\n")
        
        return execution_log


# ── CLI Interface ──
def main():
    parser = argparse.ArgumentParser(
        description="AegisNova Incident Response Playbook Automation"
    )
    parser.add_argument("--playbook", help="Playbook name to execute")
    parser.add_argument("--target", default="", help="Target (username, PID, hostname)")
    parser.add_argument("--dry-run", action="store_true", help="Show actions without executing")
    parser.add_argument("--list", action="store_true", help="List all playbooks")
    
    args = parser.parse_args()
    
    responder = IncidentResponder()
    
    if args.list:
        responder.list_playbooks()
        return
    
    if args.playbook:
        responder.execute_playbook(args.playbook, args.target, args.dry_run)
    else:
        parser.print_help()
        print("\n\nExamples:")
        print("  ir-playbook.py --list")
        print("  ir-playbook.py --playbook malware --target 1234 --dry-run")
        print("  ir-playbook.py --playbook credentials --target admin")
        print("  ir-playbook.py --playbook ransomware")


if __name__ == "__main__":
    main()
