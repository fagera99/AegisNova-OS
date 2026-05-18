#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
# AegisNova OS — Secure Boot MOK Enrollment Helper
# ═══════════════════════════════════════════════════════════
# Automates Machine Owner Key (MOK) enrollment for signed kernel
# modules and custom kernels on UEFI systems with Secure Boot.
#
# Usage: sudo aegisnova-mok-enroll [--auto] [--key <path>]
# ═══════════════════════════════════════════════════════════
set -euo pipefail

MOK_DIR="/etc/aegisnova/mok"
AUTO_MODE=false
KEY_PATH=""

log()  { echo -e "\e[1;32m[MOK]\e[0m $*"; }
err()  { echo -e "\e[1;31m[ERROR]\e[0m $*" >&2; exit 1; }
warn() { echo -e "\e[1;33m[WARN]\e[0m $*"; }

# ── Parse args ──
while [[ $# -gt 0 ]]; do
    case "$1" in
        --auto) AUTO_MODE=true; shift ;;
        --key)  KEY_PATH="$2"; shift 2 ;;
        *)      err "Unknown option: $1"; ;;
    esac
done

# ── Check root ──
[[ $EUID -eq 0 ]] || err "Must be run as root."

# ── Check UEFI / Secure Boot ──
if [[ ! -d /sys/firmware/efi ]]; then
    err "This system is not UEFI-based. MOK enrollment requires UEFI."
fi

if ! command -v mokutil &>/dev/null; then
    log "Installing mokutil ..."
    apt-get update -qq
    apt-get install -y -qq mokutil shim-signed 2>/dev/null || true
fi

# ── Check Secure Boot status ──
SB_STATUS=$(mokutil --sb-state 2>/dev/null | grep -i "secureboot" || echo "unknown")
log "Secure Boot Status: ${SB_STATUS}"

# ── Find or generate key ──
mkdir -p "${MOK_DIR}"

if [[ -n "${KEY_PATH}" && -f "${KEY_PATH}" ]]; then
    log "Using provided key: ${KEY_PATH}"
    cp "${KEY_PATH}" "${MOK_DIR}/MOK.der"
elif [[ -f "${MOK_DIR}/MOK.der" ]]; then
    log "Using existing MOK key: ${MOK_DIR}/MOK.der"
else
    log "Generating new MOK keypair ..."
    
    # Generate private key
    openssl req -new -x509 -newkey rsa:4096 \
        -keyout "${MOK_DIR}/MOK.priv" \
        -outform DER -out "${MOK_DIR}/MOK.der" \
        -days 3650 -nodes \
        -subj "/CN=AegisNova OS Secure Boot Key/"
    
    chmod 600 "${MOK_DIR}/MOK.priv"
    chmod 644 "${MOK_DIR}/MOK.der"
    
    log "MOK keypair generated."
fi

# ── Check if key is already enrolled ──
if mokutil --list-enrolled 2>/dev/null | grep -q "AegisNova"; then
    log "AegisNova MOK key is already enrolled."
    log "You can sign kernel modules with:"
    log "  /usr/src/linux-headers-$(uname -r)/scripts/sign-file sha512 \\"
    log "    ${MOK_DIR}/MOK.priv ${MOK_DIR}/MOK.der <module.ko>"
    exit 0
fi

# ── Enroll MOK ──
log "Enrolling MOK key ..."
log "You will be asked to set a one-time password for MOK enrollment."
log "This password will be required at next boot to complete enrollment."

if ${AUTO_MODE}; then
    # Generate random password for auto-enrollment
    MOK_PASSWORD=$(openssl rand -base64 32 | tr -d '=+/' | cut -c1-16)
    log "Auto-generated MOK password: ${MOK_PASSWORD}"
    log "WRITE THIS DOWN! You will need it at next boot."
    
    echo "${MOK_PASSWORD}" | mokutil --import "${MOK_DIR}/MOK.der" 2>/dev/null || true
    
    # Store password securely for reference
    echo "${MOK_PASSWORD}" > "${MOK_DIR}/MOK_PASSWORD.txt"
    chmod 600 "${MOK_DIR}/MOK_PASSWORD.txt"
    warn "MOK password saved to ${MOK_DIR}/MOK_PASSWORD.txt (secure it immediately!)"
else
    mokutil --import "${MOK_DIR}/MOK.der"
fi

# ── Sign currently installed modules ──
log "Signing installed kernel modules ..."
KERN_VER=$(uname -r)
SIGN_SCRIPT="/usr/src/linux-headers-${KERN_VER}/scripts/sign-file"

if [[ -x "${SIGN_SCRIPT}" ]]; then
    find /lib/modules/${KERN_VER}/kernel -name '*.ko' | while read -r module; do
        "${SIGN_SCRIPT}" sha512 "${MOK_DIR}/MOK.priv" "${MOK_DIR}/MOK.der" "${module}" 2>/dev/null || true
    done
    log "Kernel modules signed."
else
    warn "Kernel sign script not found. Modules may need manual signing."
fi

# ── Done ──
log ""
log "═══════════════════════════════════════════════════════════════"
log "  ✅ MOK Enrollment Initiated!"
log "═══════════════════════════════════════════════════════════════"
log ""
log "REBOOT REQUIRED to complete enrollment."
log ""
log "At next boot, you will see:"
log "  'Perform MOK management'"
log ""
log "Steps:"
log "  1. Select 'Enroll MOK'"
log "  2. Select 'Continue'"
log "  3. Enter the password you set (or: ${MOK_PASSWORD:-<your password>})"
log "  4. Select 'Reboot'"
log ""
log "After reboot, verify with: mokutil --list-enrolled"
log "═══════════════════════════════════════════════════════════════"

if ${AUTO_MODE}; then
    read -rp "Reboot now? [y/N]: " REBOOT
    [[ "${REBOOT}" =~ ^[Yy]$ ]] && reboot
fi
