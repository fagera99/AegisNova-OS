#!/usr/bin/env python3
"""
AegisNova OS — Automated Sigma Rule Generator Agent
=====================================================
Generates Sigma detection rules from natural language descriptions,
log samples, or MITRE ATT&CK techniques. Supports:
- Natural language to Sigma rule conversion
- Log sample analysis and rule extraction
- MITRE ATT&CK technique-based rule generation
- Rule validation and optimization

Usage:
    python3 sigma-generator.py --description "Detect Mimikatz usage"
    python3 sigma-generator.py --log-sample /var/log/auth.log
    python3 sigma-generator.py --technique T1003 --output rules/
    python3 sigma-generator.py --validate rule.yml
"""

import json
import os
import re
import sys
import yaml
import argparse
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

# ── Configuration ──
SIGMA_RULES_DIR = "/opt/aegisnova/sigma-rules"
SIGMA_TEMPLATES_DIR = "/opt/aegisnova/sigma-templates"

# ── Sigma Rule Templates ──
SIGMA_TEMPLATE = """title: {title}
id: {rule_id}
status: experimental
description: {description}
references:
{references}
author: AegisNova Sigma Agent
date: {date}
tags:
{tags}
logsource:
{logsource}
detection:
{detection}
falsepositives:
{falsepositives}
level: {level}
"""

# Technique to Sigma rule mappings
TECHNIQUE_TEMPLATES = {
    "T1003": {
        "title": "OS Credential Dumping - LSASS Access",
        "description": "Detects attempts to dump credentials from LSASS memory",
        "logsource": {
            "product": "windows",
            "service": "security"
        },
        "detection": {
            "selection": {
                "EventID": 4656,
                "ObjectType": "Process",
                "ObjectName": "*lsass.exe"
            },
            "condition": "selection"
        },
        "tags": ["attack.credential_access", "attack.t1003", "attack.t1003.001"],
        "level": "high"
    },
    "T1003.001": {
        "title": "Credential Dumping - LSASS Memory",
        "description": "Detects credential dumping from LSASS using Mimikatz or similar tools",
        "logsource": {
            "product": "windows",
            "service": "sysmon"
        },
        "detection": {
            "selection": {
                "EventID": 10,
                "TargetImage": "*lsass.exe",
                "GrantedAccess": ["0x1010", "0x1410", "0x143a", "0x1430", "0x1016"]
            },
            "condition": "selection"
        },
        "tags": ["attack.credential_access", "attack.t1003.001"],
        "level": "critical"
    },
    "T1059": {
        "title": "Command Execution - Scripting Interpreter",
        "description": "Detects execution via scripting interpreters",
        "logsource": {
            "product": "windows",
            "service": "sysmon"
        },
        "detection": {
            "selection": {
                "EventID": 1,
                "Image": ["*powershell.exe", "*cmd.exe", "*wscript.exe", "*cscript.exe", "*mshta.exe"]
            },
            "condition": "selection"
        },
        "tags": ["attack.execution", "attack.t1059"],
        "level": "medium"
    },
    "T1059.001": {
        "title": "PowerShell Execution",
        "description": "Detects suspicious PowerShell execution",
        "logsource": {
            "product": "windows",
            "service": "powershell"
        },
        "detection": {
            "selection": {
                "EventID": 4104,
                "ScriptBlockText": ["*Invoke-Mimikatz*", "*Invoke-Expression*", "*DownloadString*", "*EncodedCommand*"]
            },
            "condition": "selection"
        },
        "tags": ["attack.execution", "attack.t1059.001"],
        "level": "high"
    },
    "T1071": {
        "title": "Network Communication - Application Layer Protocol",
        "description": "Detects suspicious network communication via application layer protocols",
        "logsource": {
            "product": "windows",
            "service": "sysmon"
        },
        "detection": {
            "selection": {
                "EventID": 3,
                "Initiated": "true",
                "DestinationPort": ["80", "443", "8080", "8443"]
            },
            "filter": {
                "Image": ["*chrome.exe", "*firefox.exe", "*msedge.exe", "*iexplore.exe"]
            },
            "condition": "selection and not filter"
        },
        "tags": ["attack.command_and_control", "attack.t1071"],
        "level": "medium"
    },
    "T1087": {
        "title": "Account Discovery",
        "description": "Detects account enumeration activities",
        "logsource": {
            "product": "windows",
            "service": "security"
        },
        "detection": {
            "selection": {
                "EventID": ["4798", "4799", "4768", "4769"]
            },
            "condition": "selection"
        },
        "tags": ["attack.discovery", "attack.t1087"],
        "level": "low"
    },
    "T1136": {
        "title": "Account Creation",
        "description": "Detects creation of new user accounts",
        "logsource": {
            "product": "windows",
            "service": "security"
        },
        "detection": {
            "selection": {
                "EventID": ["4720", "4728", "4732", "4756"]
            },
            "condition": "selection"
        },
        "tags": ["attack.persistence", "attack.t1136"],
        "level": "medium"
    },
    "T1203": {
        "title": "Exploitation for Client Execution",
        "description": "Detects exploitation attempts for client-side execution",
        "logsource": {
            "product": "windows",
            "service": "sysmon"
        },
        "detection": {
            "selection": {
                "EventID": 7,
                "ImageLoaded": ["*shell32.dll", "*kernel32.dll", "*ntdll.dll"]
            },
            "condition": "selection"
        },
        "tags": ["attack.execution", "attack.t1203"],
        "level": "high"
    },
    "T1550": {
        "title": "Alternate Authentication Material Usage",
        "description": "Detects use of alternate authentication material",
        "logsource": {
            "product": "windows",
            "service": "security"
        },
        "detection": {
            "selection": {
                "EventID": ["4648", "4768", "4769", "4776"]
            },
            "condition": "selection"
        },
        "tags": ["attack.lateral_movement", "attack.defense_evasion", "attack.t1550"],
        "level": "high"
    },
    "T1558": {
        "title": "Kerberos Ticket Abuse",
        "description": "Detects abuse of Kerberos tickets",
        "logsource": {
            "product": "windows",
            "service": "security"
        },
        "detection": {
            "selection": {
                "EventID": ["4769", "4771", "4776"],
                "TicketOptions": ["0x40810010", "0x40800010"]
            },
            "condition": "selection"
        },
        "tags": ["attack.credential_access", "attack.t1558"],
        "level": "high"
    },
    "T1558.003": {
        "title": "Kerberoasting Activity",
        "description": "Detects Kerberoasting attempts - TGS requests with RC4 encryption",
        "logsource": {
            "product": "windows",
            "service": "security"
        },
        "detection": {
            "selection": {
                "EventID": 4769,
                "TicketEncryptionType": "0x17",
                "Status": "0x0"
            },
            "filter": {
                "ServiceName": ["*$", "krbtgt"]
            },
            "condition": "selection and not filter"
        },
        "tags": ["attack.credential_access", "attack.t1558.003"],
        "level": "high"
    },
    "T1567": {
        "title": "Data Exfiltration via Web Services",
        "description": "Detects potential data exfiltration via web services",
        "logsource": {
            "product": "windows",
            "service": "sysmon"
        },
        "detection": {
            "selection": {
                "EventID": 3,
                "DestinationHostname": ["*drive.google.com*", "*dropbox.com*", "*mega.nz*", "*pastebin.com*"]
            },
            "condition": "selection"
        },
        "tags": ["attack.exfiltration", "attack.t1567"],
        "level": "medium"
    },
    "T1574": {
        "title": "Hijack Execution Flow",
        "description": "Detects hijacking of execution flow",
        "logsource": {
            "product": "windows",
            "service": "sysmon"
        },
        "detection": {
            "selection": {
                "EventID": 7,
                "ImageLoaded": ["*\\temp\\*", "*\\users\\*", "*\\appdata\\*"]
            },
            "condition": "selection"
        },
        "tags": ["attack.persistence", "attack.privilege_escalation", "attack.t1574"],
        "level": "high"
    },
}

# Linux-specific templates
LINUX_TEMPLATES = {
    "linux_sudo_abuse": {
        "title": "Linux Sudo Abuse Detection",
        "description": "Detects potential sudo abuse and privilege escalation attempts",
        "logsource": {
            "product": "linux",
            "service": "auditd"
        },
        "detection": {
            "selection": {
                "type": "SYSCALL",
                "syscall": 59,
                "exe": ["/usr/bin/sudo", "/bin/sudo"],
                "success": "yes"
            },
            "suspicious_cmd": {
                "a0": ["*bash*", "*sh*", "*python*", "*perl*", "*ruby*"]
            },
            "condition": "selection and suspicious_cmd"
        },
        "tags": ["attack.privilege_escalation", "attack.t1548"],
        "level": "medium"
    },
    "linux_ssh_bruteforce": {
        "title": "Linux SSH Brute Force Attempts",
        "description": "Detects potential SSH brute force attacks",
        "logsource": {
            "product": "linux",
            "service": "auth"
        },
        "detection": {
            "selection": {
                "pam_unix": "authentication failure"
            },
            "timeframe": "5m",
            "condition": "selection | count() > 5"
        },
        "tags": ["attack.credential_access", "attack.t1110"],
        "level": "medium"
    },
    "linux_file_integrity": {
        "title": "Linux Critical File Modification",
        "description": "Detects modifications to critical system files",
        "logsource": {
            "product": "linux",
            "service": "auditd"
        },
        "detection": {
            "selection": {
                "type": "PATH",
                "name": ["/etc/passwd", "/etc/shadow", "/etc/sudoers", "/etc/hosts"]
            },
            "condition": "selection"
        },
        "tags": ["attack.persistence", "attack.t1098"],
        "level": "high"
    },
    "linux_reverse_shell": {
        "title": "Linux Reverse Shell Detection",
        "description": "Detects potential reverse shell connections",
        "logsource": {
            "product": "linux",
            "service": "auditd"
        },
        "detection": {
            "selection": {
                "type": "SYSCALL",
                "syscall": 59,
                "exe": ["/bin/bash", "/bin/sh", "/usr/bin/nc", "/usr/bin/netcat"],
                "a0": ["*-c*", "*bash*", "*sh*", "*/dev/tcp/*"]
            },
            "condition": "selection"
        },
        "tags": ["attack.execution", "attack.t1059"],
        "level": "high"
    },
    "linux_webshell": {
        "title": "Linux Web Shell Activity",
        "description": "Detects potential web shell activity",
        "logsource": {
            "product": "linux",
            "service": "apache"
        },
        "detection": {
            "selection": {
                "c-uri": ["*.php*", "*.jsp*", "*.asp*", "*.aspx*"],
                "cs-method": ["POST", "GET"]
            },
            "suspicious_params": {
                "c-uri": ["*cmd=*", "*exec=*", "*system=*", "*eval=*", "*shell=*"]
            },
            "condition": "selection and suspicious_params"
        },
        "tags": ["attack.persistence", "attack.t1505.003"],
        "level": "high"
    },
}


@dataclass
class SigmaRule:
    title: str
    rule_id: str
    status: str
    description: str
    references: List[str]
    author: str
    date: str
    tags: List[str]
    logsource: Dict[str, Any]
    detection: Dict[str, Any]
    falsepositives: List[str]
    level: str


class SigmaGenerator:
    """Generates Sigma detection rules."""
    
    def __init__(self):
        self.windows_templates = TECHNIQUE_TEMPLATES
        self.linux_templates = LINUX_TEMPLATES
        self.rule_counter = 0
    
    def _generate_rule_id(self) -> str:
        """Generate a unique rule ID."""
        self.rule_counter += 1
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        return f"{timestamp}-aegisnova-{self.rule_counter:04d}"
    
    def generate_from_technique(self, technique_id: str) -> Optional[SigmaRule]:
        """Generate a Sigma rule from a MITRE ATT&CK technique ID."""
        template = self.windows_templates.get(technique_id.upper())
        
        if not template:
            return None
        
        rule = SigmaRule(
            title=template["title"],
            rule_id=self._generate_rule_id(),
            status="experimental",
            description=template["description"],
            references=[
                f"https://attack.mitre.org/techniques/{technique_id.upper()}/"
            ],
            author="AegisNova Sigma Agent",
            date=datetime.utcnow().strftime("%Y/%m/%d"),
            tags=template["tags"],
            logsource=template["logsource"],
            detection=template["detection"],
            falsepositives=["Legitimate administrative activity"],
            level=template["level"]
        )
        
        return rule
    
    def generate_from_description(self, description: str) -> Optional[SigmaRule]:
        """Generate a Sigma rule from a natural language description."""
        description_lower = description.lower()
        
        # Match keywords to techniques
        technique_scores = {}
        
        for tid, template in {**self.windows_templates, **self.linux_templates}.items():
            score = 0
            title_lower = template["title"].lower()
            desc_lower = template["description"].lower()
            
            # Score based on keyword matches
            words = description_lower.split()
            for word in words:
                if len(word) > 3:
                    if word in title_lower:
                        score += 3
                    if word in desc_lower:
                        score += 2
            
            if score > 0:
                technique_scores[tid] = score
        
        if not technique_scores:
            # Generate generic rule
            return self._generate_generic_rule(description)
        
        # Use best matching template
        best_tid = max(technique_scores, key=technique_scores.get)
        return self.generate_from_technique(best_tid)
    
    def _generate_generic_rule(self, description: str) -> SigmaRule:
        """Generate a generic Sigma rule when no template matches."""
        return SigmaRule(
            title=f"AI-Generated: {description[:50]}",
            rule_id=self._generate_rule_id(),
            status="experimental",
            description=f"Automatically generated rule: {description}",
            references=["https://github.com/aegisnova/os"],
            author="AegisNova Sigma Agent",
            date=datetime.utcnow().strftime("%Y/%m/%d"),
            tags=["attack.execution"],
            logsource={
                "product": "windows",
                "service": "sysmon"
            },
            detection={
                "selection": {
                    "EventID": 1,
                    "CommandLine": "*"
                },
                "condition": "selection"
            },
            falsepositives=["Unknown - review required"],
            level="low"
        )
    
    def generate_linux_rules(self) -> List[SigmaRule]:
        """Generate all Linux-specific Sigma rules."""
        rules = []
        
        for template_id, template in self.linux_templates.items():
            rule = SigmaRule(
                title=template["title"],
                rule_id=self._generate_rule_id(),
                status="experimental",
                description=template["description"],
                references=["https://github.com/aegisnova/os"],
                author="AegisNova Sigma Agent",
                date=datetime.utcnow().strftime("%Y/%m/%d"),
                tags=template["tags"],
                logsource=template["logsource"],
                detection=template["detection"],
                falsepositives=["Legitimate administrative activity"],
                level=template["level"]
            )
            rules.append(rule)
        
        return rules
    
    def analyze_log_sample(self, log_file: str) -> List[SigmaRule]:
        """Analyze a log file and generate rules based on patterns."""
        rules = []
        
        if not os.path.exists(log_file):
            print(f"Log file not found: {log_file}")
            return rules
        
        with open(log_file, 'r', errors='ignore') as f:
            content = f.read().lower()
        
        # Pattern detection
        if 'ssh' in content and ('failed' in content or 'failure' in content):
            rules.extend(self.generate_linux_rules()[:1])  # SSH brute force
        
        if 'sudo' in content:
            rules.extend(self.generate_linux_rules()[1:2])  # Sudo abuse
        
        if 'mimikatz' in content or 'lsass' in content:
            rule = self.generate_from_technique("T1003")
            if rule:
                rules.append(rule)
        
        if 'powershell' in content or 'invoke-' in content:
            rule = self.generate_from_technique("T1059.001")
            if rule:
                rules.append(rule)
        
        return rules
    
    def validate_rule(self, rule_file: str) -> Dict[str, Any]:
        """Validate a Sigma rule file."""
        result = {
            "valid": False,
            "errors": [],
            "warnings": []
        }
        
        try:
            with open(rule_file, 'r') as f:
                rule = yaml.safe_load(f)
            
            required_fields = ["title", "logsource", "detection", "level"]
            for field in required_fields:
                if field not in rule:
                    result["errors"].append(f"Missing required field: {field}")
            
            if "detection" in rule:
                if "condition" not in rule["detection"]:
                    result["errors"].append("Missing detection condition")
            
            if not result["errors"]:
                result["valid"] = True
            
            # Warnings
            if "tags" not in rule:
                result["warnings"].append("No tags specified")
            
            if "falsepositives" not in rule:
                result["warnings"].append("No false positives documented")
            
        except yaml.YAMLError as e:
            result["errors"].append(f"YAML parsing error: {e}")
        except Exception as e:
            result["errors"].append(f"Validation error: {e}")
        
        return result
    
    def rule_to_yaml(self, rule: SigmaRule) -> str:
        """Convert SigmaRule to YAML string."""
        rule_dict = asdict(rule)
        # Clean up empty fields
        if not rule_dict["references"]:
            del rule_dict["references"]
        
        return yaml.dump(rule_dict, sort_keys=False, allow_unicode=True, width=120)


# ── CLI Interface ──
def main():
    parser = argparse.ArgumentParser(
        description="AegisNova Sigma Rule Generator Agent"
    )
    parser.add_argument("--description", help="Generate rule from description")
    parser.add_argument("--technique", help="Generate rule from ATT&CK technique ID")
    parser.add_argument("--log-sample", help="Analyze log file")
    parser.add_argument("--linux-rules", action="store_true", help="Generate all Linux rules")
    parser.add_argument("--validate", help="Validate a Sigma rule file")
    parser.add_argument("--output", "-o", default="-", help="Output file or directory")
    parser.add_argument("--format", choices=["yaml", "json"], default="yaml", help="Output format")
    
    args = parser.parse_args()
    
    generator = SigmaGenerator()
    
    if args.validate:
        result = generator.validate_rule(args.validate)
        print(json.dumps(result, indent=2))
        return
    
    rules = []
    
    if args.technique:
        rule = generator.generate_from_technique(args.technique)
        if rule:
            rules.append(rule)
        else:
            print(f"No template found for technique: {args.technique}")
            print("Generating generic rule instead...")
            rules.append(generator._generate_generic_rule(f"Technique {args.technique}"))
    
    if args.description:
        rule = generator.generate_from_description(args.description)
        if rule:
            rules.append(rule)
    
    if args.log_sample:
        rules.extend(generator.analyze_log_sample(args.log_sample))
    
    if args.linux_rules:
        rules.extend(generator.generate_linux_rules())
    
    if not rules:
        parser.print_help()
        print("\n\nExamples:")
        print("  sigma-generator.py --technique T1558.003 --output kerberoasting.yml")
        print("  sigma-generator.py --description \"Detect Mimikatz usage\"")
        print("  sigma-generator.py --linux-rules --output linux-rules/")
        print("  sigma-generator.py --validate rule.yml")
        return
    
    # Output rules
    os.makedirs(SIGMA_RULES_DIR, exist_ok=True)
    
    if args.output == "-":
        for rule in rules:
            if args.format == "yaml":
                print(generator.rule_to_yaml(rule))
            else:
                print(json.dumps(asdict(rule), indent=2))
            print("---")
    else:
        if len(rules) == 1:
            # Single file output
            with open(args.output, 'w') as f:
                if args.format == "yaml":
                    f.write(generator.rule_to_yaml(rules[0]))
                else:
                    f.write(json.dumps(asdict(rules[0]), indent=2))
            print(f"Rule saved to: {args.output}")
        else:
            # Directory output
            os.makedirs(args.output, exist_ok=True)
            for i, rule in enumerate(rules):
                filename = f"{rule.title.lower().replace(' ', '_')[:40]}_{i}.yml"
                filepath = os.path.join(args.output, filename)
                with open(filepath, 'w') as f:
                    f.write(generator.rule_to_yaml(rule))
            print(f"{len(rules)} rules saved to: {args.output}")


if __name__ == "__main__":
    main()
