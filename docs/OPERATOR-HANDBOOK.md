# AegisNova OS — Operator Handbook
# ═══════════════════════════════════════════════════════════

## Table of Contents

1. [Getting Started](#getting-started)
2. [Security Features](#security-features)
3. [AI Agents](#ai-agents)
4. [Red Team Operations](#red-team-operations)
5. [Blue Team Operations](#blue-team-operations)
6. [Incident Response](#incident-response)
7. [OSINT](#osint)
8. [System Maintenance](#system-maintenance)
9. [Troubleshooting](#troubleshooting)

---

## Getting Started

### First Boot

1. Boot from USB or VM
2. The macOS theme applies automatically
3. AI services start in the background
4. Verify services: `systemctl status ai-shell ebpf-sensor`

### Quick Setup

```bash
# Set API keys (optional)
echo 'OPENAI_API_KEY=sk-...' >> /etc/aegisnova/env
echo 'ANTHROPIC_API_KEY=sk-ant-...' >> /etc/aegisnova/env

# Initialize secrets vault
python3 /usr/local/bin/secrets-vault.py --init

# Apply security hardening
/usr/local/bin/harden-system.sh --enforce-selinux
```

---

## Security Features

### LUKS Persistence

```bash
# Setup encrypted persistence on USB
/usr/local/bin/aegisnova-persistence-setup.sh /dev/sdX
```

### Secure Boot / MOK

```bash
# Enroll Machine Owner Key
/usr/local/bin/aegisnova-mok-enroll.sh --auto
```

### YubiKey Integration

```bash
# Setup YubiKey for SSH and sudo
/usr/local/bin/aegisnova-yubikey-setup.sh --full
```

### TPM 2.0

```bash
# Seal LUKS keys to TPM
/usr/local/bin/aegisnova-yubikey-setup.sh --tpm
```

---

## AI Agents

### LLM CLI Assistant

```bash
# Query the AI
ai-shell "How do I detect Kerberoasting?"

# Check model manager
model_manager.py --list

# Query with specific model
model_manager.py -m openai_gpt4 "Explain Active Directory attacks"
```

### eBPF Telemetry Sensor

```bash
# View real-time events
journalctl -u ebpf-sensor -f

# Configure alert threshold
echo 'ALERT_THRESHOLD=high' >> /etc/aegisnova/env
systemctl restart ebpf-sensor
```

### MITRE ATT&CK Agent

```bash
# Lookup technique
mitre-attack-agent.py --lookup T1003

# Map tool to techniques
mitre-attack-agent.py --map-tool bloodhound

# Analyze logs
mitre-attack-agent.py --analyze-log /var/log/auth.log --output report.json
```

### Sigma Rule Generator

```bash
# Generate rule from technique
sigma-generator.py --technique T1558.003 --output kerberoasting.yml

# Generate Linux rules
sigma-generator.py --linux-rules --output linux-rules/

# Validate rule
sigma-generator.py --validate rule.yml
```

---

## Red Team Operations

### Tool Categories

| Category | Tools | Command |
|----------|-------|---------|
| Recon | nmap, amass, spiderfoot | `nmap -sV target` |
| Exploitation | metasploit, sqlmap | `msfconsole` |
| Post-Exploitation | empire, bloodhound | `bloodhound-python` |
| Credentials | hashcat, john | `hashcat -m 1000 hashes.txt wordlist.txt` |
| C2 | sliver, havoc | `sliver-server` |

### AutoGPT Red-Team Stack

```bash
# Start Red-Team Autopilot
systemctl start redteam-auto

# Access results
firefox http://127.0.0.1:9090
```

---

## Blue Team Operations

### Monitoring Stack

```bash
# Start Blue-Team Analyst
systemctl start blue-analyst

# Access Jupyter
firefox http://127.0.0.1:8888?token=aegisnova2024

# Access Kibana
firefox http://127.0.0.1:5601
```

### Automated Scanning

```bash
# Run vulnerability scan
/usr/local/bin/aegisnova-vulnscan.sh --now

# Setup automatic scheduling
/usr/local/bin/aegisnova-vulnscan.sh --schedule

# Generate report
/usr/local/bin/aegisnova-vulnscan.sh --now --report
```

---

## Incident Response

### Available Playbooks

| Playbook | Use Case | Severity |
|----------|----------|----------|
| malware | Malware detection | HIGH |
| credentials | Credential compromise | CRITICAL |
| lateral_movement | Lateral movement | HIGH |
| exfiltration | Data exfiltration | CRITICAL |
| ransomware | Ransomware | CRITICAL |
| insider_threat | Insider threat | HIGH |

### Running Playbooks

```bash
# List playbooks
ir-playbook.py --list

# Dry run
ir-playbook.py --playbook malware --target 1234 --dry-run

# Execute
ir-playbook.py --playbook malware --target 1234
```

### Evidence Collection

All IR playbooks automatically collect evidence to:
`/var/log/aegisnova/evidence/`

---

## OSINT

### Domain Reconnaissance

```bash
osint-agent.py --domain example.com --full --output report.json
```

### Email Investigation

```bash
osint-agent.py --email admin@example.com
```

### IP Analysis

```bash
osint-agent.py --ip 8.8.8.8
```

---

## System Maintenance

### Updates

```bash
# Check for updates
/usr/local/bin/aegisnova-update.sh --check

# Apply security updates
/usr/local/bin/aegisnova-update.sh --security-only

# Full update
/usr/local/bin/aegisnova-update.sh
```

### Secure Wiping

```bash
# Wipe memory
/usr/local/bin/aegisnova-wipe.sh --memory

# Wipe disk
/usr/local/bin/aegisnova-wipe.sh --disk /dev/sdX

# Shred file
/usr/local/bin/aegisnova-wipe.sh --file /path/to/file

# Full cleanup
/usr/local/bin/aegisnova-wipe.sh --all
```

---

## Troubleshooting

### Service Status

```bash
# Check all AegisNova services
systemctl status ai-shell ebpf-sensor mitre-attack-agent sigma-generator osint-agent ir-playbook
```

### Logs

```bash
# View AI logs
journalctl -u ai-shell -n 50

# View eBPF sensor
journalctl -u ebpf-sensor -f

# View security logs
tail -f /var/log/aegisnova/ai/safety.log
```

### Common Issues

1. **LLM server not starting**: Check disk space and model files
2. **Docker not running**: `systemctl start docker`
3. **SELinux blocking**: Check `/var/log/audit/audit.log`
4. **YubiKey not detected**: Try different USB port
5. **TPM not found**: Check `dmesg | grep -i tpm`

---

## Quick Reference

| Command | Purpose |
|---------|---------|
| `ai-shell "query"` | AI assistant |
| `model_manager.py --list` | List AI models |
| `mitre-attack-agent.py --lookup T1003` | ATT&CK lookup |
| `sigma-generator.py --technique T1003` | Generate Sigma rule |
| `osint-agent.py --domain target.com` | OSINT recon |
| `ir-playbook.py --playbook malware` | Incident response |
| `aegisnova-vulnscan.sh --now` | Vulnerability scan |
| `aegisnova-update.sh` | System update |
| `aegisnova-wipe.sh --memory` | Secure memory wipe |
| `aegisnova-persistence-setup.sh /dev/sdX` | LUKS persistence |
| `aegisnova-mok-enroll.sh --auto` | Secure Boot MOK |
| `aegisnova-yubikey-setup.sh --full` | YubiKey setup |

---

*Built with power for the security community. Use responsibly.*
