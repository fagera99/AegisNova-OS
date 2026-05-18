#!/usr/bin/env bash
# AegisNova OS — Custom ISO Generation Script
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
LIVE_BUILD_REPO="https://gitlab.com/kalilinux/build-scripts/live-build-config.git"
LIVE_BUILD_DIR="${PROJECT_ROOT}/live-build-config"
OVERLAY_SRC="${PROJECT_ROOT}/overlay"
KERNEL_DEBS_DIR="${PROJECT_ROOT}/kernel-build"
ISO_NAME="AegisNova-v1.0"
SIGN_ISO=false
GPG_KEY_ID=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --kernel-debs) KERNEL_DEBS_DIR="$2"; shift 2 ;;
        --sign)        SIGN_ISO=true; shift ;;
        --gpg-key)     GPG_KEY_ID="$2"; shift 2 ;;
        --output)      ISO_NAME="$2"; shift 2 ;;
        *)             echo "Unknown option: $1"; exit 1 ;;
    esac
done

log()  { echo -e "\e[1;35m[AegisNova ISO]\e[0m $*"; }
err()  { echo -e "\e[1;31m[ERROR]\e[0m $*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || err "Must be run as root."

# Step 1 — Clone Kali live-build-config
if [[ -d "${LIVE_BUILD_DIR}" ]]; then
    log "Pulling latest live-build-config …"
    cd "${LIVE_BUILD_DIR}" && git pull --ff-only && cd "${PROJECT_ROOT}"
else
    log "Cloning Kali live-build-config …"
    git clone --depth 1 "${LIVE_BUILD_REPO}" "${LIVE_BUILD_DIR}"
fi

# Step 2 — Inject overlay
log "Injecting AegisNova overlay …"
INCLUDES="${LIVE_BUILD_DIR}/kali-config/common/includes.chroot"
mkdir -p "${INCLUDES}"

# APT sources
mkdir -p "${INCLUDES}/etc/apt/sources.list.d"
cp "${OVERLAY_SRC}/apt/aegisnova.list" "${INCLUDES}/etc/apt/sources.list.d/" 2>/dev/null || true

# Package lists
PKG_DIR="${LIVE_BUILD_DIR}/kali-config/variant-default/package-lists"
mkdir -p "${PKG_DIR}"
for f in redteam.list.chroot blueteam.list.chroot ai-agents.list.chroot desktop-theme.list.chroot; do
    cp "${OVERLAY_SRC}/packages/${f}" "${PKG_DIR}/" 2>/dev/null || true
done

# Systemd units — copy all services
mkdir -p "${INCLUDES}/etc/systemd/system"
cp "${OVERLAY_SRC}/systemd/"*.service "${INCLUDES}/etc/systemd/system/" 2>/dev/null || true

# Enable multi-user services (background agents)
WANTS_MU="${INCLUDES}/etc/systemd/system/multi-user.target.wants"
mkdir -p "${WANTS_MU}"
for svc in ai-shell ebpf-sensor redteam-auto blue-analyst macos-theme-switcher \
           heretic-decensor ai-proxy ai-master-setup aegisnova-skills \
           mitre-attack-agent sigma-generator osint-agent ir-playbook \
           aegisnova-vulnscan aegisnova-update aegis-brain aegis-system-control; do
    ln -sf "/etc/systemd/system/${svc}.service" "${WANTS_MU}/${svc}.service" 2>/dev/null || true
done

# Enable graphical services (JARVIS UI launches on desktop login)
WANTS_GR="${INCLUDES}/etc/systemd/system/graphical.target.wants"
mkdir -p "${WANTS_GR}"
for svc in aegis-ui-server aegis-assistant-kiosk aegis-assistant; do
    ln -sf "/etc/systemd/system/${svc}.service" "${WANTS_GR}/${svc}.service" 2>/dev/null || true
done

# Scripts
mkdir -p "${INCLUDES}/usr/local/bin"
cp "${OVERLAY_SRC}/scripts/"*.sh "${INCLUDES}/usr/local/bin/" 2>/dev/null || true
cp "${OVERLAY_SRC}/scripts/"*.py "${INCLUDES}/usr/local/bin/" 2>/dev/null || true
chmod +x "${INCLUDES}/usr/local/bin/"* 2>/dev/null || true

# Docker Compose stacks
mkdir -p "${INCLUDES}/opt/aegisnova/docker"
cp "${OVERLAY_SRC}/docker/"*.yml "${INCLUDES}/opt/aegisnova/docker/" 2>/dev/null || true

# Theme assets
mkdir -p "${INCLUDES}/usr/share/backgrounds/aegisnova"
for ext in jpg jpeg png svg; do
    find "${OVERLAY_SRC}/theme/wallpapers/" -maxdepth 1 -name "*.${ext}" \
        -exec cp {} "${INCLUDES}/usr/share/backgrounds/aegisnova/" \; 2>/dev/null || true
done
mkdir -p "${INCLUDES}/opt/aegisnova/theme"
cp "${OVERLAY_SRC}/theme/install-macos-theme.sh" "${INCLUDES}/opt/aegisnova/theme/" 2>/dev/null || true
mkdir -p "${INCLUDES}/etc/aegisnova"
cp "${OVERLAY_SRC}/theme/macos-theme.conf" "${INCLUDES}/etc/aegisnova/" 2>/dev/null || true
cp "${OVERLAY_SRC}/etc/aegisnova/model-manager.conf" "${INCLUDES}/etc/aegisnova/" 2>/dev/null || true

# AI logging directories
mkdir -p "${INCLUDES}/var/log/aegisnova/ai"
mkdir -p "${INCLUDES}/var/log/aegisnova/scans"
mkdir -p "${INCLUDES}/var/log/aegisnova/reports"
mkdir -p "${INCLUDES}/var/log/aegisnova/evidence"
mkdir -p "${INCLUDES}/var/log/aegisnova/incident-response"
mkdir -p "${INCLUDES}/var/log/aegisnova/updates"

# AegisNova vault directory
mkdir -p "${INCLUDES}/etc/aegisnova/vault"
chmod 700 "${INCLUDES}/etc/aegisnova/vault" 2>/dev/null || true

# Sigma rules directory
mkdir -p "${INCLUDES}/opt/aegisnova/sigma-rules"

# OSINT reports directory
mkdir -p "${INCLUDES}/opt/aegisnova/osint-reports"

# MITRE ATT&CK data directory
mkdir -p "${INCLUDES}/opt/aegisnova/attack-data"

# YubiKey/TPM config directories
mkdir -p "${INCLUDES}/etc/aegisnova/yubikey"
mkdir -p "${INCLUDES}/etc/aegisnova/tpm"
chmod 700 "${INCLUDES}/etc/aegisnova/yubikey" 2>/dev/null || true
chmod 700 "${INCLUDES}/etc/aegisnova/tpm" 2>/dev/null || true

# Vulnerability scan config
mkdir -p "${INCLUDES}/etc/aegisnova"
cp "${OVERLAY_SRC}/sysctl/model-manager.conf.example" "${INCLUDES}/etc/aegisnova/model-manager.conf.example" 2>/dev/null || true

# Sysctl / firewall / SSH hardening
mkdir -p "${INCLUDES}/etc/sysctl.d"
cp "${OVERLAY_SRC}/sysctl/99-aegisnova-hardening.conf" "${INCLUDES}/etc/sysctl.d/" 2>/dev/null || true
cp "${OVERLAY_SRC}/firewall/nftables.conf" "${INCLUDES}/etc/nftables.conf" 2>/dev/null || true
mkdir -p "${INCLUDES}/etc/ssh/sshd_config.d"
cp "${OVERLAY_SRC}/ssh/aegisnova-hardened.conf" "${INCLUDES}/etc/ssh/sshd_config.d/" 2>/dev/null || true

# Autostart / Legal
mkdir -p "${INCLUDES}/etc/skel/.config/autostart"
cp "${OVERLAY_SRC}/autostart/"*.desktop "${INCLUDES}/etc/skel/.config/autostart/" 2>/dev/null || true
cp "${PROJECT_ROOT}/LEGAL_NOTICE.md" "${INCLUDES}/etc/aegisnova/" 2>/dev/null || true

log "✅ Overlay injected."

# Step 3 — Inject custom kernel
if ls "${KERNEL_DEBS_DIR}"/linux-*.deb 1>/dev/null 2>&1; then
    log "Staging custom kernel .deb packages …"
    mkdir -p "${LIVE_BUILD_DIR}/kali-config/common/packages"
    cp "${KERNEL_DEBS_DIR}"/linux-*.deb "${LIVE_BUILD_DIR}/kali-config/common/packages/"
fi

# Step 3b — Build and inject meta-packages
log "Building meta-packages ..."
for meta in redteam-meta blueteam-meta; do
    if [[ -d "${PROJECT_ROOT}/meta-packages/${meta}" ]]; then
        cd "${PROJECT_ROOT}/meta-packages/${meta}"
        dpkg-deb --build . "/tmp/${meta}.deb" 2>/dev/null || true
        if [[ -f "/tmp/${meta}.deb" ]]; then
            cp "/tmp/${meta}.deb" "${LIVE_BUILD_DIR}/kali-config/common/packages/"
            log "  ${meta}.deb staged."
        fi
        cd "${PROJECT_ROOT}"
    fi
done

# Step 3c — Copy live-build hooks
log "Staging live-build hooks ..."
HOOKS_DIR="${LIVE_BUILD_DIR}/kali-config/common/hooks/normal"
mkdir -p "${HOOKS_DIR}"
# APT keyring hook MUST run first (lowest number = earliest execution)
cp "${OVERLAY_SRC}/scripts/0010-apt-keys.hook.chroot" "${HOOKS_DIR}/0010-apt-keys.hook.chroot" 2>/dev/null || true
cp "${OVERLAY_SRC}/scripts/aegisnova-bootmenu-hook.sh" "${HOOKS_DIR}/0950-aegisnova-bootmenu.hook.chroot" 2>/dev/null || true
chmod +x "${HOOKS_DIR}/"*.hook.chroot 2>/dev/null || true

INSTALLER_HOOKS="${LIVE_BUILD_DIR}/kali-config/common/hooks/live"
mkdir -p "${INSTALLER_HOOKS}"
cp "${OVERLAY_SRC}/scripts/aegisnova-installer-hook.sh" "${INSTALLER_HOOKS}/0050-aegisnova-installer.hook" 2>/dev/null || true
chmod +x "${INSTALLER_HOOKS}/"*.hook 2>/dev/null || true

# Step 3d — Copy installer welcome scripts
cp "${OVERLAY_SRC}/scripts/aegisnova-install.sh" "${INCLUDES}/usr/local/bin/" 2>/dev/null || true
cp "${OVERLAY_SRC}/scripts/aegisnova-welcome.sh" "${INCLUDES}/usr/local/bin/" 2>/dev/null || true
chmod +x "${INCLUDES}/usr/local/bin/aegisnova-install.sh" 2>/dev/null || true
chmod +x "${INCLUDES}/usr/local/bin/aegisnova-welcome.sh" 2>/dev/null || true

# Step 3e — Copy JARVIS UI and assistant assets
log "Staging JARVIS neural interface UI ..."
mkdir -p "${INCLUDES}/opt/aegisnova/assistant/ui"
# Copy the JARVIS HTML (both from assistant-ui dir and from project root demo)
cp "${OVERLAY_SRC}/scripts/assistant-ui/index.html" "${INCLUDES}/opt/aegisnova/assistant/ui/index.html" 2>/dev/null || true
cp "${PROJECT_ROOT}/demo.html" "${INCLUDES}/opt/aegisnova/assistant/ui/demo.html" 2>/dev/null || true
cp "${OVERLAY_SRC}/scripts/brain_agent_codex.py" "${INCLUDES}/usr/local/bin/" 2>/dev/null || true

# Step 4 — Build the ISO
log "Starting live-build ..."
cd "${LIVE_BUILD_DIR}"
./build.sh --verbose --arch amd64 --distribution kali-rolling \
    --bootappend-live "boot=live components quiet splash persistence" 2>&1 | tee "${PROJECT_ROOT}/iso-build.log"

# ── Locate the built ISO (live-build places it in current dir = LIVE_BUILD_DIR) ──
BUILT_ISO_NAME=$(find . -maxdepth 1 -name '*.iso' -printf '%f\n' 2>/dev/null | head -1)
[[ -n "${BUILT_ISO_NAME}" ]] || err "No .iso file produced by live-build! Check iso-build.log"

# Step 4b — Make ISO hybrid (bootable from USB via dd)
if command -v isohybrid &>/dev/null; then
    log "Making ISO hybrid for USB boot ..."
    isohybrid "${LIVE_BUILD_DIR}/${BUILT_ISO_NAME}" 2>/dev/null || true
elif command -v xorriso &>/dev/null; then
    log "ISO is already hybrid-compatible (built with xorriso)."
fi

mv "${BUILT_ISO_NAME}" "${PROJECT_ROOT}/${ISO_NAME}.iso"
cd "${PROJECT_ROOT}"
log "✅ ISO built: ${ISO_NAME}.iso ($(du -sh ${ISO_NAME}.iso | cut -f1))"

# Step 5 — Sign ISO
if $SIGN_ISO; then
    sha512sum "${ISO_NAME}.iso" > "${ISO_NAME}.iso.sha512"
    if [[ -n "${GPG_KEY_ID}" ]]; then
        gpg --default-key "${GPG_KEY_ID}" --detach-sign --armor "${ISO_NAME}.iso"
    else
        gpg --detach-sign --armor "${ISO_NAME}.iso"
    fi
    log "✅ ISO signed."
fi

log "═══════════════════════════════════════════════════════════════"
log "  ✅ ISO GENERATION COMPLETE: ${ISO_NAME}.iso"
log "═══════════════════════════════════════════════════════════════"
