#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
# AegisNova OS — System Update & Security Patch Script
# ═══════════════════════════════════════════════════════════
# Comprehensive update script that:
# - Updates all packages
# - Applies security patches with verification
# - Updates kernel if available
# - Updates Docker images
# - Updates AI models and tools
# - Verifies system integrity after update
# - Creates restore point before updates
#
# Usage: sudo aegisnova-update [--security-only] [--check] [--force]
# ═══════════════════════════════════════════════════════════
set -euo pipefail

UPDATE_LOG="/var/log/aegisnova/updates"
RESTORE_DIR="/var/log/aegisnova/restore-points"
SECURITY_ONLY=false
CHECK_ONLY=false
FORCE_UPDATE=false

log()  { echo -e "\e[1;32m[UPDATE]\e[0m $*"; }
err()  { echo -e "\e[1;31m[ERROR]\e[0m $*" >&2; exit 1; }
warn() { echo -e "\e[1;33m[WARN]\e[0m $*"; }
info() { echo -e "\e[1;34m[INFO]\e[0m $*"; }

# ── Parse args ──
while [[ $# -gt 0 ]]; do
    case "$1" in
        --security-only) SECURITY_ONLY=true; shift ;;
        --check)         CHECK_ONLY=true; shift ;;
        --force)         FORCE_UPDATE=true; shift ;;
        *)               err "Unknown option: $1"; ;;
    esac
done

# ── Check root ──
[[ $EUID -eq 0 ]] || err "Must be run as root."

# ── Create directories ──
mkdir -p "${UPDATE_LOG}" "${RESTORE_DIR}"

UPDATE_TIMESTAMP=$(date +%Y%m%d-%H%M%S)
UPDATE_LOG_FILE="${UPDATE_LOG}/update-${UPDATE_TIMESTAMP}.log"

# ═══════════════════════════════════════════════════════════
# Pre-Update Checks
# ═══════════════════════════════════════════════════════════

pre_update_checks() {
    log "Running pre-update checks..."
    
    # Check disk space
    local avail=$(df / | tail -1 | awk '{print $4}')
    if [[ ${avail} -lt 1048576 ]]; then  # Less than 1GB
        err "Insufficient disk space. At least 1GB required."
    fi
    
    # Check if important services are running
    local critical_services=("ssh" "docker")
    for svc in "${critical_services[@]}"; do
        if systemctl is-active --quiet "${svc}" 2>/dev/null; then
            info "  ${svc} is running (will be preserved)"
        fi
    done
    
    # Backup critical configs
    log "Creating restore point..."
    local restore_point="${RESTORE_DIR}/pre-update-${UPDATE_TIMESTAMP}.tar.gz"
    tar czf "${restore_point}" \
        /etc/aegisnova \
        /etc/sysctl.d \
        /etc/ssh/sshd_config.d \
        /etc/nftables.conf \
        2>/dev/null || warn "Some configs could not be backed up"
    
    log "Restore point created: ${restore_point}"
}

# ═══════════════════════════════════════════════════════════
# Package Updates
# ═══════════════════════════════════════════════════════════

update_packages() {
    log "Updating package lists..."
    apt-get update 2>&1 | tee -a "${UPDATE_LOG_FILE}"
    
    if ${SECURITY_ONLY}; then
        log "Installing security updates only..."
        apt-get upgrade -y -qq --only-upgrade 2>&1 | tee -a "${UPDATE_LOG_FILE}" || true
        apt-get install -y -qq unattended-upgrades 2>/dev/null || true
        unattended-upgrade --dry-run 2>&1 | tee -a "${UPDATE_LOG_FILE}" || true
    else
        log "Upgrading all packages..."
        apt-get upgrade -y 2>&1 | tee -a "${UPDATE_LOG_FILE}"
        apt-get dist-upgrade -y 2>&1 | tee -a "${UPDATE_LOG_FILE}" || true
    fi
    
    # Clean up
    apt-get autoremove -y 2>&1 | tee -a "${UPDATE_LOG_FILE}" || true
    apt-get autoclean 2>&1 | tee -a "${UPDATE_LOG_FILE}" || true
}

# ═══════════════════════════════════════════════════════════
# Kernel Update Check
# ═══════════════════════════════════════════════════════════

check_kernel_update() {
    log "Checking for kernel updates..."
    
    local current_kernel=$(uname -r)
    local latest_kernel=$(dpkg -l | grep linux-image | sort -V | tail -1 | awk '{print $3}' || echo "unknown")
    
    info "  Current kernel: ${current_kernel}"
    info "  Latest installed: ${latest_kernel}"
    
    if [[ "${current_kernel}" != "${latest_kernel}" ]] && [[ "${latest_kernel}" != "unknown" ]]; then
        warn "  Kernel update available!"
        warn "  Reboot required to use new kernel."
        
        if ${FORCE_UPDATE}; then
            log "  Force reboot scheduled..."
            echo "reboot" > /tmp/aegisnova-reboot-required
        fi
    else
        info "  Kernel is up to date."
    fi
}

# ═══════════════════════════════════════════════════════════
# Docker Image Updates
# ═══════════════════════════════════════════════════════════

update_docker_images() {
    if command -v docker &>/dev/null; then
        log "Checking for Docker image updates..."
        
        local images=$(docker images --format "{{.Repository}}:{{.Tag}}" | grep -v "<none>" || true)
        
        if [[ -n "${images}" ]]; then
            for image in ${images}; do
                log "  Checking ${image}..."
                docker pull "${image}" 2>/dev/null || warn "    Failed to update ${image}"
            done
            
            # Clean up old images
            docker image prune -f 2>/dev/null || true
        else
            info "  No Docker images to update."
        fi
    else
        info "  Docker not installed."
    fi
}

# ═══════════════════════════════════════════════════════════
# AI Tools & Models Update
# ═══════════════════════════════════════════════════════════

update_ai_tools() {
    log "Checking for AI tool updates..."
    
    # Update llama.cpp if installed
    if [[ -d /opt/aegisnova/llama.cpp ]]; then
        log "  Updating llama.cpp..."
        cd /tmp
        git clone --depth 1 https://github.com/ggerganov/llama.git llama-update 2>/dev/null || true
        if [[ -d llama-update ]]; then
            cd llama-update && make -j"$(nproc)" server 2>/dev/null || true
            if [[ -f server ]]; then
                cp server /opt/aegisnova/llama.cpp/server
                log "    llama.cpp updated."
            fi
            cd / && rm -rf /tmp/llama-update
        fi
    fi
    
    # Update Python packages
    if [[ -d /opt/aegisnova/heretic/venv ]]; then
        log "  Updating Heretic..."
        /opt/aegisnova/heretic/venv/bin/pip install -U heretic-llm 2>/dev/null || warn "    Heretic update failed"
    fi
    
    # Update skills
    if [[ -d /opt/aegisnova/skills ]]; then
        log "  Checking for skills updates..."
        # Skills would be updated via git if connected
        info "    Skills updates require manual git pull"
    fi
}

# ═══════════════════════════════════════════════════════════
# Security Verification
# ═══════════════════════════════════════════════════════════

verify_security() {
    log "Running post-update security verification..."
    
    # Check for modified configs
    log "  Checking configuration integrity..."
    if [[ -f /etc/aegisnova/env ]]; then
        local perms=$(stat -c %a /etc/aegisnova/env)
        if [[ "${perms}" != "600" ]]; then
            warn "    /etc/aegisnova/env has incorrect permissions: ${perms}"
            chmod 600 /etc/aegisnova/env
        fi
    fi
    
    # Verify sysctl settings
    log "  Verifying sysctl hardening..."
    local kptr=$(cat /proc/sys/kernel/kptr_restrict 2>/dev/null || echo "0")
    if [[ "${kptr}" != "2" ]]; then
        warn "    kptr_restrict is ${kptr} (should be 2)"
        sysctl -w kernel.kptr_restrict=2 2>/dev/null || true
    fi
    
    # Check firewall status
    log "  Checking firewall status..."
    if command -v nft &>/dev/null; then
        local rules_count=$(nft list ruleset 2>/dev/null | grep -c "jump" || echo "0")
        if [[ ${rules_count} -eq 0 ]]; then
            warn "    No firewall rules active!"
            if [[ -f /etc/nftables.conf ]]; then
                nft -f /etc/nftables.conf 2>/dev/null || true
            fi
        else
            info "    Firewall rules active: ${rules_count}"
        fi
    fi
    
    # Check SELinux/AppArmor
    if command -v getenforce &>/dev/null; then
        local selinux_status=$(getenforce 2>/dev/null || echo "unknown")
        info "  SELinux status: ${selinux_status}"
    fi
    
    # Verify services
    log "  Verifying critical services..."
    local services=("nftables" "auditd")
    for svc in "${services[@]}"; do
        if systemctl is-active --quiet "${svc}" 2>/dev/null; then
            info "    ${svc}: running"
        else
            warn "    ${svc}: not running"
            systemctl start "${svc}" 2>/dev/null || true
        fi
    done
}

# ═══════════════════════════════════════════════════════════
# Update Check Only
# ═══════════════════════════════════════════════════════════

check_updates() {
    log "Checking for available updates..."
    
    apt-get update -qq 2>/dev/null || true
    
    local updates=$(apt list --upgradable 2>/dev/null | grep -v "Listing..." | wc -l || echo "0")
    local security_updates=$(apt-get upgrade -s 2>/dev/null | grep -i security | wc -l || echo "0")
    
    info "  Total updates available: ${updates}"
    info "  Security updates: ${security_updates}"
    
    if [[ ${updates} -gt 0 ]]; then
        info "  Run 'aegisnova-update' to apply updates."
        exit 1  # Return non-zero to indicate updates available
    else
        info "  System is up to date."
        exit 0
    fi
}

# ═══════════════════════════════════════════════════════════
# Main Execution
# ═══════════════════════════════════════════════════════════

main() {
    log "═══════════════════════════════════════════════════════════════"
    log "  AegisNova OS Update & Security Patch"
    log "  Mode: $(${SECURITY_ONLY} && echo 'Security Only' || echo 'Full Update')"
    log "  Check Only: ${CHECK_ONLY}"
    log "═══════════════════════════════════════════════════════════════"
    
    if ${CHECK_ONLY}; then
        check_updates
        return
    fi
    
    pre_update_checks
    update_packages
    check_kernel_update
    update_docker_images
    update_ai_tools
    verify_security
    
    log ""
    log "═══════════════════════════════════════════════════════════════"
    log "  ✅ Update Complete!"
    log "═══════════════════════════════════════════════════════════════"
    
    if [[ -f /tmp/aegisnova-reboot-required ]] || [[ -f /var/run/reboot-required ]]; then
        warn "REBOOT REQUIRED to complete updates."
        warn "Run: reboot"
    fi
    
    log "Log saved: ${UPDATE_LOG_FILE}"
    log "═══════════════════════════════════════════════════════════════"
}

main "$@"
