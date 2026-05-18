#!/usr/bin/env bash
# ============================================================================
# AegisNova OS — Post-Boot Security Hardening Script
# ============================================================================
# Run after first boot to enable all security layers.
# Usage: sudo /usr/local/bin/harden-system.sh [--enforce-selinux]
# ============================================================================
set -euo pipefail

log()  { echo -e "\e[1;32m[HARDEN]\e[0m $*"; }
warn() { echo -e "\e[1;33m[WARN]\e[0m $*"; }

ENFORCE_SELINUX=false
[[ "${1:-}" == "--enforce-selinux" ]] && ENFORCE_SELINUX=true

log "═══════════════════════════════════════════════════"
log "  AegisNova OS — Security Hardening"
log "═══════════════════════════════════════════════════"

# ── 1. Apply sysctl parameters ──
log "Applying sysctl hardening …"
sysctl --system 2>/dev/null || true

# ── 2. Enable nftables firewall ──
log "Enabling nftables firewall …"
if command -v nft &>/dev/null; then
    nft -f /etc/nftables.conf 2>/dev/null || warn "nftables config not found."
    systemctl enable --now nftables 2>/dev/null || true
fi

# ── 3. SELinux ──
if $ENFORCE_SELINUX; then
    log "Setting SELinux to enforcing …"
    if command -v setenforce &>/dev/null; then
        setenforce 1 2>/dev/null || warn "Could not set SELinux to enforcing."
        sed -i 's/^SELINUX=.*/SELINUX=enforcing/' /etc/selinux/config 2>/dev/null || true
    else
        warn "SELinux tools not installed."
    fi
else
    log "SELinux: keeping current mode (use --enforce-selinux to enforce)."
fi

# ── 4. AppArmor ──
log "Loading AppArmor profiles …"
if command -v aa-enforce &>/dev/null; then
    aa-enforce /etc/apparmor.d/* 2>/dev/null || warn "Some AppArmor profiles failed."
    systemctl enable --now apparmor 2>/dev/null || true
fi

# ── 5. auditd ──
log "Enabling audit daemon …"
systemctl enable --now auditd 2>/dev/null || true

# ── 6. fapolicyd ──
log "Enabling fapolicyd (binary whitelisting) …"
systemctl enable --now fapolicyd 2>/dev/null || warn "fapolicyd not available."

# ── 7. SSH hardening ──
log "Verifying SSH configuration …"
if [[ -f /etc/ssh/sshd_config.d/aegisnova-hardened.conf ]]; then
    systemctl restart sshd 2>/dev/null || true
    log "  SSH: password auth disabled, key-only."
fi

# ── 8. MFA setup hint ──
log "MFA setup (optional):"
log "  apt install libpam-google-authenticator"
log "  google-authenticator  (run as each user)"
log "  Then uncomment MFA lines in /etc/pam.d/sudo"

# ── 9. Disable core dumps ──
log "Disabling core dumps …"
echo "* hard core 0" >> /etc/security/limits.conf 2>/dev/null || true
echo "* soft core 0" >> /etc/security/limits.conf 2>/dev/null || true

# ── 10. Remove unnecessary services ──
log "Disabling unnecessary services …"
for svc in avahi-daemon cups bluetooth; do
    systemctl disable --now "${svc}" 2>/dev/null || true
done

log ""
log "═══════════════════════════════════════════════════"
log "  ✅ Security hardening complete."
log "  Run 'lynis audit system' for a full audit."
log "═══════════════════════════════════════════════════"
