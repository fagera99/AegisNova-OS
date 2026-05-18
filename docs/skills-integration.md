# AegisNova OS Agent Skills Integration

## Overview

AegisNova OS integrates **1000+ Agent Skills** from the [awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills) repository, covering:

- 🔴 **Red Team Security Skills** - Offensive security, penetration testing
- 🔵 **Blue Team Security Skills** - Defensive security, monitoring, IR
- 🎨 **Design/UI/UX Skills** - Interface design, user experience

## Total Skills Breakdown

| Category | Subcategory | Skills Count |
|----------|-------------|--------------|
| **Security** | Trail of Bits | 20+ |
| **Security** | Sentry | 8+ |
| **Security** | OpenAI Security | 3 |
| **Security** | Datadog | 4 |
| **Security** | Auth0 | 5 |
| **Security** | Community | 10+ |
| **Security** | Anthropic Cybersecurity | 753 |
| **Design** | Anthropic Design | 6 |
| **Design** | Google Labs | 5 |
| **Design** | Vercel | 4 |
| **TOTAL** | | **1000+** |

## Installation

Skills are automatically installed on first boot via `aegisnova-skills.service`.

```bash
# Manual installation
sudo bash /usr/local/bin/aegisnova-skills-installer.sh

# Update skills
aegisnova-skills --update
```

## Usage

### CLI Commands

```bash
# List all skills
aegisnova-skills --list

# List security skills only
aegisnova-skills --list security

# List design skills only
aegisnova-skills --list design

# Search for specific skills
aegisnova-skills --search vulnerability
aegisnova-skills --search "static analysis"
aegisnova-skills --search design

# View skill details
aegisnova-skills --use trailofbits/static-analysis
aegisnova-skills --use vibesec

# Show categories
aegisnova-skills --categories

# Show statistics
aegisnova-skills --stats
```

### AI Agents Integration

Skills are automatically available to all AI agents:

```bash
# Use skills via ai-shell
ai-shell --skill trailofbits/static-analysis "Audit this Python code for SQL injection"

# Use skills via model_manager
ai-model --skill sentry-workflow "Set up error monitoring for this app"

# Use design skills
ai-shell --skill anthropic/frontend-design "Create a security dashboard UI"
```

## Security Skills Catalog

### Trail of Bits (Offensive & Defensive)

| Skill | Purpose | Use Case |
|-------|---------|----------|
| `burpsuite-project-parser` | Parse Burp Suite scans | Web app pentesting |
| `static-analysis` | CodeQL/Semgrep/SARIF | Vulnerability discovery |
| `semgrep-rule-creator` | Custom vulnerability rules | Signature creation |
| `variant-analysis` | Find similar vulnerabilities | Vulnerability research |
| `insecure-defaults` | Detect misconfigurations | System hardening |
| `sharp-edges` | Dangerous API detection | Code review |
| `constant-time-analysis` | Timing side-channels | Crypto auditing |
| `differential-review` | Security-focused diff review | Code review |
| `building-secure-contracts` | Smart contract security | Blockchain auditing |
| `entry-point-analyzer` | Smart contract entry points | DeFi security |

### Sentry (Monitoring & Incident Response)

| Skill | Purpose | Use Case |
|-------|---------|----------|
| `sentry-workflow` | End-to-end incident response | Production issues |
| `sentry-fix-issues` | Automated issue fixing | Bug triage |
| `sentry-create-alert` | Alert configuration | SOC monitoring |
| `sentry-feature-setup` | Advanced monitoring setup | Infrastructure |
| `sentry-otel-exporter-setup` | OpenTelemetry pipeline | Distributed tracing |

### Datadog (Log Analysis)

| Skill | Purpose | Use Case |
|-------|---------|----------|
| `dd-logs` | Log search and analysis | SIEM operations |
| `dd-monitors` | Monitor management | Infrastructure monitoring |
| `dd-apm` | Application performance | Anomaly detection |
| `dd-pup` | CLI for Datadog API | Lightweight monitoring |

### Auth0 (Identity & Authentication)

| Skill | Purpose | Use Case |
|-------|---------|----------|
| `auth0-mfa` | Multi-factor authentication | Identity hardening |
| `auth0-migration` | Identity migration | Auth transitions |
| `auth0-quickstart` | Auth0 integration | Secure authentication |
| `auth0-aspnetcore-api` | JWT validation | API security |

### Community Security Tools

| Skill | Purpose | Use Case |
|-------|---------|----------|
| `clawsec` | Automated audits | Security automation |
| `ffuf-claude-skill` | Web fuzzing | Directory discovery |
| `vibesec` | Secure coding assistant | Prevent XSS/SQLi/IDOR |
| `varlock-claude-skill` | Secret management | Prevent secret leaks |
| `defense-in-depth` | Layered security | Architecture review |
| `rootly-incident-responder` | AI-powered IR | Incident management |
| `cso` | Threat modeling | OWASP + STRIDE |
| `canary` | Post-deploy monitoring | Security regression |
| `security-bluebook-builder` | Security playbooks | Documentation |

### Anthropic Cybersecurity Collection (753 Skills)

Comprehensive cybersecurity coverage across 38 domains:
- Cloud Security
- Penetration Testing
- Red Teaming
- Digital Forensics & Incident Response (DFIR)
- Malware Analysis
- Threat Intelligence
- Network Security
- Application Security
- And 31 more domains...

**All mapped to MITRE ATT&CK framework!**

## Design Skills Catalog

### Anthropic Design

| Skill | Purpose | Use Case |
|-------|---------|----------|
| `algorithmic-art` | Generative art with p5.js | Security visualizations |
| `canvas-design` | PNG/PDF design | Report generation |
| `frontend-design` | UI/UX development | Security dashboards |
| `theme-factory` | Professional themes | Theming system |
| `web-artifacts-builder` | Complex HTML artifacts | Web reports |
| `brand-guidelines` | Brand application | Corporate identity |

### Google Labs Stitch

| Skill | Purpose | Use Case |
|-------|---------|----------|
| `design-md` | DESIGN.md management | Design documentation |
| `enhance-prompt` | Prompt improvement | Better AI responses |
| `react-components` | React component generation | Dashboard building |
| `shadcn-ui` | UI component library | Interface building |
| `stitch-loop` | Design-to-code iteration | Rapid prototyping |

### Vercel Design

| Skill | Purpose | Use Case |
|-------|---------|----------|
| `react-best-practices` | React patterns | Dashboard development |
| `web-design-guidelines` | Design standards | Interface consistency |
| `composition-patterns` | Component composition | Reusable UI |
| `next-best-practices` | Next.js patterns | Web applications |

## Integration with AI Agents

### Red Team Agent

```bash
# Automatic skill selection based on task
redteam-agent "Scan for SQL injection"
→ Uses: ffuf-claude-skill, vibesec

redteam-agent "Audit smart contracts"
→ Uses: trailofbits/building-secure-contracts

redteam-agent "Create phishing page"
→ Uses: anthropic/frontend-design, vibesec
```

### Blue Team Agent

```bash
# Monitoring setup
blue-agent "Set up log monitoring"
→ Uses: sentry-workflow, dd-logs

# Incident response
blue-agent "Investigate breach"
→ Uses: rootly-incident-responder, clawsec

# Threat modeling
blue-agent "Model threats for this app"
→ Uses: cso, security-threat-model
```

### Design Agent

```bash
# Security dashboard
ai-shell "Design security monitoring dashboard"
→ Uses: frontend-design, react-components, theme-factory

# Report generation
ai-shell "Create pentest report template"
→ Uses: canvas-design, web-artifacts-builder
```

## File Locations

```
/opt/aegisnova/skills/
├── awesome-agent-skills/          # Original repo (read-only)
└── aegisnova/                     # Active skills
    ├── index.json                 # Skills index
    ├── security/
    │   ├── trailofbits/          # Trail of Bits skills
    │   ├── sentry/               # Sentry skills
    │   ├── openai/               # OpenAI security
    │   ├── datadog/              # Datadog skills
    │   ├── auth0/                # Auth0 skills
    │   ├── community/            # Community tools
    │   └── anthropic-cyber/      # 753 cybersecurity skills
    └── design/
        ├── anthropic/            # Anthropic design
        ├── google-labs/          # Google Labs Stitch
        └── vercel/               # Vercel design
```

## Configuration

Edit `/etc/aegisnova/model-manager.conf` to configure skill usage:

```json
{
  "skills": {
    "enabled": true,
    "auto_select": true,
    "categories": ["security", "design"],
    "security": {
      "trailofbits": true,
      "sentry": true,
      "community": true,
      "anthropic-cyber": true
    },
    "design": {
      "anthropic": true,
      "google-labs": true,
      "vercel": true
    }
  }
}
```

## Updating Skills

```bash
# Update all skills from repository
aegisnova-skills --update

# Or manually
cd /opt/aegisnova/skills/awesome-agent-skills
git pull
bash /usr/local/bin/aegisnova-skills-installer.sh
```

## Logs

```bash
# Installation logs
journalctl -u aegisnova-skills

# Skills usage
/var/log/aegisnova/skills-install.log

# Audit logs
/var/log/aegisnova/ai/audit.log
```

## Security Notes

1. **All skills are read-only** - Cannot modify system without explicit permission
2. **Audit logging** - Every skill usage is logged
3. **Sandboxed** - Skills run in isolated environment
4. **Community skills** - Reviewed before inclusion
5. **Update verification** - Git signatures verified on update

## Troubleshooting

### Skills not found

```bash
# Reinstall skills
bash /usr/local/bin/aegisnova-skills-installer.sh

# Check installation
ls -la /opt/aegisnova/skills/aegisnova/
```

### CLI not working

```bash
# Make sure CLI is executable
chmod +x /usr/local/bin/aegisnova-skills

# Test
aegisnova-skills --help
```

### Missing dependencies

```bash
# Install git (required for cloning)
apt update && apt install -y git

# Install Python (for JSON parsing)
apt install -y python3
```

## References

- [awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills)
- [Trail of Bits Skills](https://officialskills.sh/trailofbits)
- [Anthropic Cybersecurity](https://github.com/mukul975/Anthropic-Cybersecurity-Skills)
- [Sentry Skills](https://officialskills.sh/getsentry)
