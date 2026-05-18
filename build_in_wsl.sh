#!/bin/bash
# ═══════════════════════════════════════════════════════════
# AegisNova OS — WSL2 Build Script
# Run as root inside Kali WSL
# ═══════════════════════════════════════════════════════════
set -euo pipefail

# Paths
WIN_PROJECT="/mnt/e/Linux_AI"
BUILD_ROOT="/tmp/aegisnova-build"
LIVE_BUILD_REPO="https://gitlab.com/kalilinux/build-scripts/live-build-config.git"
ISO_OUTPUT="/mnt/e/AegisNova-v1.0.iso"

log()  { echo -e "\e[1;35m[AegisNova Build]\e[0m $*"; }
err()  { echo -e "\e[1;31m[ERROR]\e[0m $*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || err "Must be run as root. Use: wsl -d kali-linux -u root -e bash /mnt/e/Linux_AI/build_in_wsl.sh"

# ── Step 0: Install dependencies ──
log "Installing build dependencies ..."
apt-get update -qq
apt-get install -y -qq \
    live-build \
    git \
    curl \
    wget \
    xorriso \
    isolinux \
    syslinux-efi \
    grub-efi-amd64-bin \
    dosfstools \
    squashfs-tools \
    debootstrap \
    dpkg-dev \
    qemu-utils \
    2>&1 | tail -5

# ── Step 1: Clean & prepare build directory ──
log "Preparing build environment ..."
rm -rf "${BUILD_ROOT}"
mkdir -p "${BUILD_ROOT}"

# Copy project to native Linux filesystem (fixes NTFS permission issues)
log "Copying project to Linux filesystem ..."
cp -r "${WIN_PROJECT}" "${BUILD_ROOT}/Linux_AI"
cd "${BUILD_ROOT}/Linux_AI"

# Fix permissions
chmod +x custom_iso.sh
chmod +x overlay/scripts/*.sh 2>/dev/null || true
chmod +x overlay/scripts/*.py 2>/dev/null || true
chmod +x overlay/scripts/*.hook* 2>/dev/null || true
chmod +x overlay/scripts/*.hook.chroot 2>/dev/null || true
chmod +x overlay/live-build-hooks/*.hook* 2>/dev/null || true
find overlay/scripts/ -type f -name "*.sh" -exec chmod +x {} \; 2>/dev/null || true
find overlay/scripts/ -type f -name "*.py" -exec chmod +x {} \; 2>/dev/null || true

# ── Step 2: Run the ISO build ──
log "Starting ISO build (this will take 30-90 minutes) ..."
./custom_iso.sh --output AegisNova-v1.0 2>&1 | tee build.log

# ── Step 3: Move ISO back to Windows drive ──
if [[ -f "AegisNova-v1.0.iso" ]]; then
    log "✅ Build complete! Moving ISO to E: drive ..."
    mv AegisNova-v1.0.iso "${ISO_OUTPUT}"
    log "ISO location: ${ISO_OUTPUT}"
    log "Size: $(du -sh "${ISO_OUTPUT}" | cut -f1)"
    log ""
    log "To flash to USB (from Windows PowerShell as Admin):"
    log "  wsl -d kali-linux -e bash -c \"dd if=${ISO_OUTPUT} of=/dev/sdX bs=4M status=progress conv=fsync\""
    log "  (Replace /dev/sdX with your USB device, e.g. /dev/sdb)"
else
    err "ISO build failed! Check ${BUILD_ROOT}/Linux_AI/build.log"
fi

# Cleanup
log "Cleaning up build directory ..."
cd /
rm -rf "${BUILD_ROOT}"

log "✅ All done!"
