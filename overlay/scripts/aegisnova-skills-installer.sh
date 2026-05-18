#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
# AegisNova OS — Awesome Agent Skills Installer
# Installs 1000+ curated skills for Red/Blue Team + Design
# ═══════════════════════════════════════════════════════════
set -euo pipefail

SKILLS_DIR="/opt/aegisnova/skills"
REPO_DIR="${SKILLS_DIR}/awesome-agent-skills"
AEGISNOVA_SKILLS_DIR="${SKILLS_DIR}/aegisnova"
LOG_FILE="/var/log/aegisnova/skills-install.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() { echo -e "${BLUE}[Skills]${NC} $*" | tee -a "${LOG_FILE}"; }
success() { echo -e "${GREEN}[✓]${NC} $*" | tee -a "${LOG_FILE}"; }
warn() { echo -e "${YELLOW}[!]${NC} $*" | tee -a "${LOG_FILE}"; }
error() { echo -e "${RED}[✗]${NC} $*" | tee -a "${LOG_FILE}"; }

# Create directories
mkdir -p "${SKILLS_DIR}" "${AEGISNOVA_SKILLS_DIR}" "$(dirname "${LOG_FILE}")"

echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║     AegisNova OS - Agent Skills Installer                   ║"
echo "║     1000+ Skills for Red/Blue Team + Design                 ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# ═══════════════════════════════════════════════════════════
# PHASE 1: Clone awesome-agent-skills repository
# ═══════════════════════════════════════════════════════════
log "Phase 1: Cloning awesome-agent-skills repository..."

if [[ -d "${REPO_DIR}" ]]; then
    log "Repository exists, updating..."
    cd "${REPO_DIR}" && git pull --ff-only
else
    log "Cloning repository..."
    git clone --depth 1 https://github.com/VoltAgent/awesome-agent-skills.git "${REPO_DIR}"
fi

success "Repository cloned/updated"

# ═══════════════════════════════════════════════════════════
# PHASE 2: Install Security Skills (Priority)
# ═══════════════════════════════════════════════════════════
log ""
log "Phase 2: Installing Security Skills..."

# Trail of Bits Security Skills (20 skills)
log "Installing Trail of Bits security skills..."
mkdir -p "${AEGISNOVA_SKILLS_DIR}/security/trailofbits"
cd "${REPO_DIR}"

TRAILOFBITS_SKILLS=(
    "trailofbits/ask-questions-if-underspecified"
    "trailofbits/audit-context-building"
    "trailofbits/building-secure-contracts"
    "trailofbits/burpsuite-project-parser"
    "trailofbits/claude-in-chrome-troubleshooting"
    "trailofbits/constant-time-analysis"
    "trailofbits/culture-index"
    "trailofbits/differential-review"
    "trailofbits/dwarf-expert"
    "trailofbits/entry-point-analyzer"
    "trailofbits/firebase-apk-scanner"
    "trailofbits/insecure-defaults"
    "trailofbits/modern-python"
    "trailofbits/property-based-testing"
    "trailofbits/semgrep-rule-creator"
    "trailofbits/semgrep-rule-variant-creator"
    "trailofbits/sharp-edges"
    "trailofbits/spec-to-code-compliance"
    "trailofbits/static-analysis"
    "trailofbits/testing-handbook-skills"
    "trailofbits/variant-analysis"
)

for skill in "${TRAILOFBITS_SKILLS[@]}"; do
    skill_name=$(basename "${skill}")
    if [[ -d "${REPO_DIR}/skills/${skill}" ]] || [[ -f "${REPO_DIR}/skills/${skill}.md" ]]; then
        cp -r "${REPO_DIR}/skills/${skill}" "${AEGISNOVA_SKILLS_DIR}/security/trailofbits/" 2>/dev/null || \
        cp "${REPO_DIR}/skills/${skill}.md" "${AEGISNOVA_SKILLS_DIR}/security/trailofbits/" 2>/dev/null || true
        success "Installed: ${skill_name}"
    else
        warn "Not found: ${skill}"
    fi
done

# Sentry Skills (Monitoring & IR)
log "Installing Sentry monitoring skills..."
mkdir -p "${AEGISNOVA_SKILLS_DIR}/security/sentry"

SENTRY_SKILLS=(
    "getsentry/sentry-sdk-setup"
    "getsentry/sentry-workflow"
    "getsentry/sentry-fix-issues"
    "getsentry/sentry-code-review"
    "getsentry/sentry-pr-code-review"
    "getsentry/sentry-create-alert"
    "getsentry/sentry-feature-setup"
    "getsentry/sentry-otel-exporter-setup"
)

for skill in "${SENTRY_SKILLS[@]}"; do
    skill_name=$(basename "${skill}")
    if [[ -d "${REPO_DIR}/skills/${skill}" ]] || [[ -f "${REPO_DIR}/skills/${skill}.md" ]]; then
        cp -r "${REPO_DIR}/skills/${skill}" "${AEGISNOVA_SKILLS_DIR}/security/sentry/" 2>/dev/null || \
        cp "${REPO_DIR}/skills/${skill}.md" "${AEGISNOVA_SKILLS_DIR}/security/sentry/" 2>/dev/null || true
        success "Installed: ${skill_name}"
    fi
done

# OpenAI Security Skills
log "Installing OpenAI security skills..."
mkdir -p "${AEGISNOVA_SKILLS_DIR}/security/openai"

OPENAI_SECURITY_SKILLS=(
    "openai/security-best-practices"
    "openai/security-threat-model"
    "openai/security-ownership-map"
)

for skill in "${OPENAI_SECURITY_SKILLS[@]}"; do
    skill_name=$(basename "${skill}")
    if [[ -d "${REPO_DIR}/skills/${skill}" ]] || [[ -f "${REPO_DIR}/skills/${skill}.md" ]]; then
        cp -r "${REPO_DIR}/skills/${skill}" "${AEGISNOVA_SKILLS_DIR}/security/openai/" 2>/dev/null || \
        cp "${REPO_DIR}/skills/${skill}.md" "${AEGISNOVA_SKILLS_DIR}/security/openai/" 2>/dev/null || true
        success "Installed: ${skill_name}"
    fi
done

# Datadog Skills
log "Installing Datadog monitoring skills..."
mkdir -p "${AEGISNOVA_SKILLS_DIR}/security/datadog"

DATADOG_SKILLS=(
    "datadog/dd-logs"
    "datadog/dd-monitors"
    "datadog/dd-apm"
    "datadog/dd-pup"
)

for skill in "${DATADOG_SKILLS[@]}"; do
    skill_name=$(basename "${skill}")
    if [[ -d "${REPO_DIR}/skills/${skill}" ]] || [[ -f "${REPO_DIR}/skills/${skill}.md" ]]; then
        cp -r "${REPO_DIR}/skills/${skill}" "${AEGISNOVA_SKILLS_DIR}/security/datadog/" 2>/dev/null || \
        cp "${REPO_DIR}/skills/${skill}.md" "${AEGISNOVA_SKILLS_DIR}/security/datadog/" 2>/dev/null || true
        success "Installed: ${skill_name}"
    fi
done

# Auth0 Skills
log "Installing Auth0 identity skills..."
mkdir -p "${AEGISNOVA_SKILLS_DIR}/security/auth0"

AUTH0_SKILLS=(
    "auth0/auth0-mfa"
    "auth0/auth0-migration"
    "auth0/auth0-quickstart"
    "auth0/auth0-aspnetcore-api"
    "auth0/auth0-fastify-api"
)

for skill in "${AUTH0_SKILLS[@]}"; do
    skill_name=$(basename "${skill}")
    if [[ -d "${REPO_DIR}/skills/${skill}" ]] || [[ -f "${REPO_DIR}/skills/${skill}.md" ]]; then
        cp -r "${REPO_DIR}/skills/${skill}" "${AEGISNOVA_SKILLS_DIR}/security/auth0/" 2>/dev/null || \
        cp "${REPO_DIR}/skills/${skill}.md" "${AEGISNOVA_SKILLS_DIR}/security/auth0/" 2>/dev/null || true
        success "Installed: ${skill_name}"
    fi
done

# Community Security Skills
log "Installing community security skills..."
mkdir -p "${AEGISNOVA_SKILLS_DIR}/security/community"

COMMUNITY_SECURITY_SKILLS=(
    "clawsec"
    "ffuf-claude-skill"
    "vibesec"
    "varlock-claude-skill"
    "defense-in-depth"
    "rootly-incident-responder"
    "security-bluebook-builder"
    "cso"
    "canary"
    "investigate"
)

for skill in "${COMMUNITY_SECURITY_SKILLS[@]}"; do
    if [[ -d "${REPO_DIR}/skills/community/${skill}" ]] || [[ -f "${REPO_DIR}/skills/community/${skill}.md" ]]; then
        cp -r "${REPO_DIR}/skills/community/${skill}" "${AEGISNOVA_SKILLS_DIR}/security/community/" 2>/dev/null || \
        cp "${REPO_DIR}/skills/community/${skill}.md" "${AEGISNOVA_SKILLS_DIR}/security/community/" 2>/dev/null || true
        success "Installed: ${skill}"
    fi
done

# ═══════════════════════════════════════════════════════════
# PHASE 3: Install Anthropic Cybersecurity Skills (753 skills)
# ═══════════════════════════════════════════════════════════
log ""
log "Phase 3: Installing Anthropic Cybersecurity Skills (753 skills)..."
mkdir -p "${AEGISNOVA_SKILLS_DIR}/security/anthropic-cyber"

# Try to find and install the large cybersecurity skills collection
if [[ -d "${REPO_DIR}/skills/anthropics" ]]; then
    log "Found Anthropic skills, copying..."
    cp -r "${REPO_DIR}/skills/anthropics/"* "${AEGISNOVA_SKILLS_DIR}/security/anthropic-cyber/" 2>/dev/null || true
    success "Anthropic skills installed"
elif [[ -d "${REPO_DIR}/skills/mukul975" ]]; then
    log "Found mukul975 cybersecurity skills..."
    cp -r "${REPO_DIR}/skills/mukul975/"* "${AEGISNOVA_SKILLS_DIR}/security/anthropic-cyber/" 2>/dev/null || true
    success "Cybersecurity skills collection installed"
else
    warn "Large cybersecurity skills collection not found in repo"
    log "You can manually add it later from: https://github.com/mukul975/Anthropic-Cybersecurity-Skills"
fi

# ═══════════════════════════════════════════════════════════
# PHASE 4: Install Design/UI/UX Skills
# ═══════════════════════════════════════════════════════════
log ""
log "Phase 4: Installing Design/UI/UX Skills..."
mkdir -p "${AEGISNOVA_SKILLS_DIR}/design"

# Anthropic Design Skills
ANTHROPIC_DESIGN_SKILLS=(
    "anthropics/algorithmic-art"
    "anthropics/canvas-design"
    "anthropics/frontend-design"
    "anthropics/theme-factory"
    "anthropics/web-artifacts-builder"
    "anthropics/brand-guidelines"
)

for skill in "${ANTHROPIC_DESIGN_SKILLS[@]}"; do
    skill_name=$(basename "${skill}")
    if [[ -d "${REPO_DIR}/skills/${skill}" ]] || [[ -f "${REPO_DIR}/skills/${skill}.md" ]]; then
        cp -r "${REPO_DIR}/skills/${skill}" "${AEGISNOVA_SKILLS_DIR}/design/" 2>/dev/null || \
        cp "${REPO_DIR}/skills/${skill}.md" "${AEGISNOVA_SKILLS_DIR}/design/" 2>/dev/null || true
        success "Installed: ${skill_name}"
    fi
done

# Google Labs Stitch Skills
log "Installing Google Labs Stitch design skills..."
mkdir -p "${AEGISNOVA_SKILLS_DIR}/design/google-labs"

GOOGLE_DESIGN_SKILLS=(
    "google-labs-code/design-md"
    "google-labs-code/enhance-prompt"
    "google-labs-code/react-components"
    "google-labs-code/shadcn-ui"
    "google-labs-code/stitch-loop"
)

for skill in "${GOOGLE_DESIGN_SKILLS[@]}"; do
    skill_name=$(basename "${skill}")
    if [[ -d "${REPO_DIR}/skills/${skill}" ]] || [[ -f "${REPO_DIR}/skills/${skill}.md" ]]; then
        cp -r "${REPO_DIR}/skills/${skill}" "${AEGISNOVA_SKILLS_DIR}/design/google-labs/" 2>/dev/null || \
        cp "${REPO_DIR}/skills/${skill}.md" "${AEGISNOVA_SKILLS_DIR}/design/google-labs/" 2>/dev/null || true
        success "Installed: ${skill_name}"
    fi
done

# Vercel Design Skills
log "Installing Vercel design skills..."
mkdir -p "${AEGISNOVA_SKILLS_DIR}/design/vercel"

VERCEL_DESIGN_SKILLS=(
    "vercel-labs/react-best-practices"
    "vercel-labs/web-design-guidelines"
    "vercel-labs/composition-patterns"
    "vercel-labs/next-best-practices"
)

for skill in "${VERCEL_DESIGN_SKILLS[@]}"; do
    skill_name=$(basename "${skill}")
    if [[ -d "${REPO_DIR}/skills/${skill}" ]] || [[ -f "${REPO_DIR}/skills/${skill}.md" ]]; then
        cp -r "${REPO_DIR}/skills/${skill}" "${AEGISNOVA_SKILLS_DIR}/design/vercel/" 2>/dev/null || \
        cp "${REPO_DIR}/skills/${skill}.md" "${AEGISNOVA_SKILLS_DIR}/design/vercel/" 2>/dev/null || true
        success "Installed: ${skill_name}"
    fi
done

# ═══════════════════════════════════════════════════════════
# PHASE 5: Create Skills Index & Metadata
# ═══════════════════════════════════════════════════════════
log ""
log "Phase 5: Creating skills index..."

cat > "${AEGISNOVA_SKILLS_DIR}/index.json" << 'EOF'
{
  "name": "AegisNova OS Agent Skills",
  "version": "1.0",
  "total_skills": 0,
  "categories": {
    "security": {
      "description": "Red/Blue Team security skills",
      "subcategories": {
        "trailofbits": "Trail of Bits security research",
        "sentry": "Monitoring and incident response",
        "openai": "OpenAI security tools",
        "datadog": "Log analysis and monitoring",
        "auth0": "Identity and authentication",
        "community": "Community security tools",
        "anthropic-cyber": "Comprehensive cybersecurity (753 skills)"
      }
    },
    "design": {
      "description": "UI/UX and design skills",
      "subcategories": {
        "anthropic": "Anthropic design tools",
        "google-labs": "Google Labs Stitch",
        "vercel": "Vercel web design"
      }
    }
  },
  "usage": {
    "list": "aegisnova-skills --list",
    "search": "aegisnova-skills --search <keyword>",
    "use": "aegisnova-skills --use <skill-name>"
  }
}
EOF

# Count actual skills installed
SKILL_COUNT=$(find "${AEGISNOVA_SKILLS_DIR}" -type f -name "*.md" -o -name "*.json" | wc -l)
log "Total skill files installed: ${SKILL_COUNT}"

# Update index with actual count
sed -i "s/\"total_skills\": 0/\"total_skills\": ${SKILL_COUNT}/" "${AEGISNOVA_SKILLS_DIR}/index.json"

# ═══════════════════════════════════════════════════════════
# PHASE 6: Create CLI Wrapper
# ═══════════════════════════════════════════════════════════
log ""
log "Phase 6: Creating CLI wrapper..."

cat > "/usr/local/bin/aegisnova-skills" << 'SCRIPT'
#!/usr/bin/env bash
# AegisNova OS Skills CLI

SKILLS_DIR="/opt/aegisnova/skills/aegisnova"
INDEX_FILE="${SKILLS_DIR}/index.json"

show_help() {
    echo "AegisNova OS Agent Skills Manager"
    echo ""
    echo "Usage:"
    echo "  aegisnova-skills --list              List all installed skills"
    echo "  aegisnova-skills --list security     List security skills"
    echo "  aegisnova-skills --list design       List design skills"
    echo "  aegisnova-skills --search <keyword>  Search skills"
    echo "  aegisnova-skills --use <skill>       Use a specific skill"
    echo "  aegisnova-skills --categories        Show categories"
    echo "  aegisnova-skills --update            Update skills from repo"
    echo "  aegisnova-skills --stats             Show statistics"
    echo ""
}

list_skills() {
    local category="${1:-all}"
    
    if [[ "${category}" == "all" ]] || [[ "${category}" == "security" ]]; then
        echo "=== SECURITY SKILLS ==="
        find "${SKILLS_DIR}/security" -type f \( -name "*.md" -o -name "*.json" \) | while read f; do
            basename "$f"
        done | sort | uniq
        echo ""
    fi
    
    if [[ "${category}" == "all" ]] || [[ "${category}" == "design" ]]; then
        echo "=== DESIGN SKILLS ==="
        find "${SKILLS_DIR}/design" -type f \( -name "*.md" -o -name "*.json" \) | while read f; do
            basename "$f"
        done | sort | uniq
        echo ""
    fi
}

search_skills() {
    local keyword="$1"
    echo "Searching for: ${keyword}"
    echo ""
    find "${SKILLS_DIR}" -type f \( -name "*.md" -o -name "*.json" \) | xargs grep -l "${keyword}" 2>/dev/null | while read f; do
        echo "  - $(basename "$f") ($(dirname "$f" | sed 's|/opt/aegisnova/skills/aegisnova/||'))"
    done
}

use_skill() {
    local skill="$1"
    local skill_file=$(find "${SKILLS_DIR}" -type f -name "${skill}*" | head -1)
    
    if [[ -f "${skill_file}" ]]; then
        echo "=== Skill: ${skill} ==="
        cat "${skill_file}"
    else
        echo "Skill not found: ${skill}"
        echo "Use --search to find it"
    fi
}

show_stats() {
    echo "AegisNova OS Skills Statistics"
    echo "=============================="
    echo ""
    
    if [[ -f "${INDEX_FILE}" ]]; then
        cat "${INDEX_FILE}" | python3 -m json.tool 2>/dev/null || cat "${INDEX_FILE}"
    fi
    
    echo ""
    echo "File counts:"
    find "${SKILLS_DIR}" -type d -maxdepth 2 | while read dir; do
        local count=$(find "$dir" -type f | wc -l)
        if [[ ${count} -gt 0 ]]; then
            local name=$(echo "$dir" | sed 's|/opt/aegisnova/skills/aegisnova/||')
            echo "  ${name}: ${count} files"
        fi
    done
}

# Main
case "${1:-}" in
    --list|-l)
        list_skills "${2:-all}"
        ;;
    --search|-s)
        search_skills "${2:-}"
        ;;
    --use|-u)
        use_skill "${2:-}"
        ;;
    --categories|-c)
        echo "Security Categories:"
        ls -1 "${SKILLS_DIR}/security" 2>/dev/null || echo "  (none)"
        echo ""
        echo "Design Categories:"
        ls -1 "${SKILLS_DIR}/design" 2>/dev/null || echo "  (none)"
        ;;
    --update|-up)
        echo "Updating skills..."
        bash /usr/local/bin/aegisnova-skills-installer.sh
        ;;
    --stats|-st)
        show_stats
        ;;
    --help|-h|*)
        show_help
        ;;
esac
SCRIPT

chmod +x "/usr/local/bin/aegisnova-skills"
success "CLI wrapper created"

# ═══════════════════════════════════════════════════════════
# PHASE 7: Final Summary
# ═══════════════════════════════════════════════════════════
log ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗"
echo "║              INSTALLATION COMPLETE                            ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo "Installed Categories:"
echo "  🔴 Security:"
echo "     • Trail of Bits (20+ skills)"
echo "     • Sentry (8+ skills)"
echo "     • OpenAI Security (3 skills)"
echo "     • Datadog (4 skills)"
echo "     • Auth0 (5 skills)"
echo "     • Community Security (10+ skills)"
echo "     • Anthropic Cybersecurity (753 skills)"
echo ""
echo "  🎨 Design/UI/UX:"
echo "     • Anthropic Design (6 skills)"
echo "     • Google Labs Stitch (5 skills)"
echo "     • Vercel Design (4 skills)"
echo ""
echo "Total: ${SKILL_COUNT} skill files"
echo ""
echo "Usage:"
echo "  aegisnova-skills --list"
echo "  aegisnova-skills --search vulnerability"
echo "  aegisnova-skills --stats"
echo ""
echo "Location: /opt/aegisnova/skills/aegisnova/"
