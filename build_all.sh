#!/bin/bash
# ═══════════════════════════════════════════════════════════
# AegisNova — Complete Build (Kernel + ISO) on WSL2 ext4
# Run: wsl -d kali-linux -u root -e bash /mnt/e/Linux_AI/build_all.sh
# ═══════════════════════════════════════════════════════════
set -euo pipefail

WIN_PROJ="/mnt/e/Linux_AI"
BUILD_DIR="/tmp/aegisnova-build"
KERNEL_TARBALL="https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-6.12.30.tar.xz"
LIVE_BUILD_REPO="https://gitlab.com/kalilinux/build-scripts/live-build-config.git"

log()  { echo -e "\e[1;35m[AegisNova]\e[0m $*"; }
err()  { echo -e "\e[1;31m[ERROR]\e[0m $*" >&2; exit 1; }

mkdir -p "${BUILD_DIR}"
cd "${BUILD_DIR}"

# ═══════════════════════════════════════════════════════════
# Step 0 — Fix APT (IPv4 only, avoid broken mirrors)
# ═══════════════════════════════════════════════════════════
log "Fixing APT configuration ..."
cat > /etc/apt/apt.conf.d/99force-ipv4 << 'EOF'
Acquire::ForceIPv4 "true";
Acquire::Retries "3";
Acquire::http::Timeout "30";
EOF

# Use a direct working mirror
rm -f /etc/apt/sources.list.d/* 2>/dev/null || true
cat > /etc/apt/sources.list << 'EOF'
deb [arch=amd64] http://http.kali.org/kali kali-rolling main contrib non-free non-free-firmware
deb [arch=amd64] http://http.kali.org/kali kali-last-snapshot main contrib non-free non-free-firmware
EOF

apt-get clean
rm -rf /var/lib/apt/lists/*
apt-get update -qq || apt-get update

# ═══════════════════════════════════════════════════════════
# Step 1 — Install build dependencies
# ═══════════════════════════════════════════════════════════
log "Installing build dependencies (this takes ~5 min) ..."
apt-get install -y -qq --no-install-recommends \
    live-build git curl wget xorriso isolinux \
    dosfstools squashfs-tools debootstrap dpkg-dev \
    build-essential bc bison flex libncurses-dev libssl-dev \
    libelf-dev dwarves 2>&1 | tail -5 || true

# ═══════════════════════════════════════════════════════════
# Step 2 — Download & build kernel on ext4
# ═══════════════════════════════════════════════════════════
log "Downloading kernel source to ext4 ..."
if [[ ! -f "linux-6.12.30.tar.xz" ]]; then
    curl -fsSL -o linux-6.12.30.tar.xz "${KERNEL_TARBALL}" || \
    wget -q "${KERNEL_TARBALL}" -O linux-6.12.30.tar.xz
fi

tar -xf linux-6.12.30.tar.xz
cd linux-6.12.30

# Copy .config from Windows project
cp "${WIN_PROJ}/kernel-build/linux-6.12.30/.config" . 2>/dev/null || \
  cp "${WIN_PROJ}/kernel-build/.config" . 2>/dev/null || \
  make defconfig

# Git init for deb-pkg
git init --quiet
git add -A
git commit -m 'initial' --quiet

log "Building kernel .deb packages (this takes 15-30 min on 14 cores) ..."
make -j$(nproc) deb-pkg LOCALVERSION='-aegisnova' KDEB_PKGVERSION='1.0.0-1' 2>&1 | tee "${BUILD_DIR}/kernel-build.log"

# Copy .deb back to Windows
log "Staging kernel debs ..."
mkdir -p "${WIN_PROJ}/kernel-build"
cp "${BUILD_DIR}"/*.deb "${WIN_PROJ}/kernel-build/" 2>/dev/null || true
KERNEL_DEBS="${WIN_PROJ}/kernel-build"

# ═══════════════════════════════════════════════════════════
# Step 3 — Clone live-build and prepare
# ═══════════════════════════════════════════════════════════
cd "${BUILD_DIR}"
LIVE_BUILD_DIR="${BUILD_DIR}/live-build-config"

if [[ -d "${LIVE_BUILD_DIR}" ]]; then
    cd "${LIVE_BUILD_DIR}" && git pull --ff-only && cd "${BUILD_DIR}"
else
    git clone --depth 1 "${LIVE_BUILD_REPO}" "${LIVE_BUILD_DIR}"
fi

# ═══════════════════════════════════════════════════════════
# Step 4 — Copy project to Linux filesystem for ISO build
# ═══════════════════════════════════════════════════════════
log "Copying project to ext4 for ISO build ..."
rm -rf "${BUILD_DIR}/Linux_AI"
cp -r "${WIN_PROJ}" "${BUILD_DIR}/Linux_AI"
cd "${BUILD_DIR}/Linux_AI"

# Fix all permissions
chmod +x custom_iso.sh
find overlay/scripts/ -type f \( -name '*.sh' -o -name '*.py' \) -exec chmod +x {} \; 2>/dev/null || true
find overlay/scripts/ -type f -name '*.hook*' -exec chmod +x {} \; 2>/dev/null || true

# ═══════════════════════════════════════════════════════════
# Step 5 — Build ISO
# ═══════════════════════════════════════════════════════════
log "Starting ISO build (this takes 30-60 min) ..."
./custom_iso.sh --kernel-debs "${KERNEL_DEBS}" --output AegisNova-v1.0 2>&1 | tee "${BUILD_DIR}/iso-build.log"

# ═══════════════════════════════════════════════════════════
# Step 6 — Move ISO back to Windows
# ═══════════════════════════════════════════════════════════
if [[ -f "AegisNova-v1.0.iso" ]]; then
    log "✅ ISO built successfully!"
    mv AegisNova-v1.0.iso "${WIN_PROJ}/"
    log "Location: ${WIN_PROJ}/AegisNova-v1.0.iso"
    log "Size: $(du -sh "${WIN_PROJ}/AegisNova-v1.0.iso" | cut -f1)"
    log ""
    log "To flash to USB (from Windows PowerShell as Admin):"
    log "  wsl -d kali-linux -u root -e bash -c \"dd if=${WIN_PROJ}/AegisNova-v1.0.iso of=/dev/sdX bs=4M status=progress conv=fsync\""
else
    err "ISO build failed! Check ${BUILD_DIR}/iso-build.log"
fi

# Cleanup
log "Cleaning up ..."
cd /
rm -rf "${BUILD_DIR}"

log "✅ ALL DONE!"
