#!/bin/bash
# AegisNova ISO Build on ext4 (fixes WSL2 NTFS tar issue)
set -euo pipefail

WIN_PROJ="/mnt/e/Linux_AI"
BUILD_DIR="/tmp/aegisnova-iso-build"
LIVE_BUILD_REPO="https://gitlab.com/kalilinux/build-scripts/live-build-config.git"

log()  { echo -e "\e[1;35m[AegisNova ISO]\e[0m $*"; }
err()  { echo -e "\e[1;31m[ERROR]\e[0m $*" >&2; exit 1; }

mkdir -p "${BUILD_DIR}"
cd "${BUILD_DIR}"

# 1. Clone live-build-config to ext4
if [[ -d "${BUILD_DIR}/live-build-config" ]]; then
    cd "${BUILD_DIR}/live-build-config" && git pull --ff-only && cd "${BUILD_DIR}"
else
    git clone --depth 1 "${LIVE_BUILD_REPO}" "${BUILD_DIR}/live-build-config"
fi

# 2. Copy our overlay into live-build-config
LBC="${BUILD_DIR}/live-build-config"
INCLUDES="${LBC}/kali-config/common/includes.chroot"
mkdir -p "${INCLUDES}"

# Copy packages lists
PKG_DIR="${LBC}/kali-config/variant-default/package-lists"
mkdir -p "${PKG_DIR}"
for f in redteam.list.chroot blueteam.list.chroot ai-agents.list.chroot desktop-theme.list.chroot; do
    cp "${WIN_PROJ}/overlay/packages/${f}" "${PKG_DIR}/" 2>/dev/null || true
done

# Copy systemd services
mkdir -p "${INCLUDES}/etc/systemd/system"
cp "${WIN_PROJ}/overlay/systemd/"*.service "${INCLUDES}/etc/systemd/system/" 2>/dev/null || true

# Enable services
WANTS_MU="${INCLUDES}/etc/systemd/system/multi-user.target.wants"
mkdir -p "${WANTS_MU}"
for svc in ai-shell ebpf-sensor redteam-auto blue-analyst macos-theme-switcher \
           heretic-decensor ai-proxy ai-master-setup aegisnova-skills \
           mitre-attack-agent sigma-generator osint-agent ir-playbook \
           aegisnova-vulnscan aegisnova-update aegis-brain aegis-system-control; do
    ln -sf "/etc/systemd/system/${svc}.service" "${WANTS_MU}/${svc}.service" 2>/dev/null || true
done

WANTS_GR="${INCLUDES}/etc/systemd/system/graphical.target.wants"
mkdir -p "${WANTS_GR}"
for svc in aegis-ui-server aegis-assistant-kiosk aegis-assistant; do
    ln -sf "/etc/systemd/system/${svc}.service" "${WANTS_GR}/${svc}.service" 2>/dev/null || true
done

# Copy scripts
mkdir -p "${INCLUDES}/usr/local/bin"
for script in \
    aegisnova-assistant.py aegisnova-brain.py aegis-system-control.py \
    aegisnova-mitre-attack-agent.py aegisnova-sigma-generator.py \
    aegisnova-osint-agent.py aegisnova-ir-playbook.py \
    aegisnova-vulnscan.sh aegisnova-update.sh aegisnova-wipe.sh \
    aegisnova-skills-installer.sh aegisnova-persistence-setup.sh \
    aegisnova-mok-enroll.sh aegisnova-yubikey-setup.sh \
    aegisnova-install.sh aegisnova-welcome.sh \
    ai-master-setup.sh ai_proxy.py ai-shell-launcher.sh \
    ai-shell-setup.sh ai-shell.sh macos-theme-switcher.sh \
    ebpf-sensor.py secrets-vault.py model_manager.py \
    skills_integration.py agent.py brain_agent_codex.py; do
    cp "${WIN_PROJ}/overlay/scripts/${script}" "${INCLUDES}/usr/local/bin/" 2>/dev/null || true
    chmod +x "${INCLUDES}/usr/local/bin/${script}" 2>/dev/null || true
done
ln -sf /usr/local/bin/ai_proxy.py "${INCLUDES}/usr/local/bin/ai-proxy.py" 2>/dev/null || true

# Copy UI
mkdir -p "${INCLUDES}/opt/aegisnova/assistant/ui"
cp "${WIN_PROJ}/demo.html" "${INCLUDES}/opt/aegisnova/assistant/ui/index.html" 2>/dev/null || true
cp "${WIN_PROJ}/demo.html" "${INCLUDES}/opt/aegisnova/assistant/ui/demo.html" 2>/dev/null || true
cp "${WIN_PROJ}/overlay/scripts/assistant-ui/kda-dashboard.html" "${INCLUDES}/opt/aegisnova/assistant/ui/" 2>/dev/null || true

# Copy hooks
HOOKS_DIR="${LBC}/kali-config/common/hooks/normal"
mkdir -p "${HOOKS_DIR}"
cp "${WIN_PROJ}/overlay/scripts/0010-apt-keys.hook.chroot" "${HOOKS_DIR}/" 2>/dev/null || true
cp "${WIN_PROJ}/overlay/scripts/aegisnova-bootmenu-hook.sh" "${HOOKS_DIR}/0950-aegisnova-bootmenu.hook.chroot" 2>/dev/null || true
chmod +x "${HOOKS_DIR}/"*.hook.chroot 2>/dev/null || true

INSTALLER_HOOKS="${LBC}/kali-config/common/hooks/live"
mkdir -p "${INSTALLER_HOOKS}"
cp "${WIN_PROJ}/overlay/scripts/aegisnova-installer-hook.sh" "${INSTALLER_HOOKS}/0050-aegisnova-installer.hook" 2>/dev/null || true
chmod +x "${INSTALLER_HOOKS}/"*.hook 2>/dev/null || true

# Copy APT sources
mkdir -p "${INCLUDES}/etc/apt/sources.list.d"
cp "${WIN_PROJ}/overlay/apt/aegisnova.list" "${INCLUDES}/etc/apt/sources.list.d/" 2>/dev/null || true

# Copy kernel debs
if ls "${WIN_PROJ}/kernel-build/"linux-*.deb 1>/dev/null 2>&1; then
    mkdir -p "${LBC}/kali-config/common/packages"
    cp "${WIN_PROJ}/kernel-build/"linux-*.deb "${LBC}/kali-config/common/packages/"
    log "Custom kernel staged."
fi

# Copy meta-packages
for meta in redteam-meta blueteam-meta; do
    if [[ -d "${WIN_PROJ}/meta-packages/${meta}" ]]; then
        cd "${WIN_PROJ}/meta-packages/${meta}"
        dpkg-deb --build . "/tmp/${meta}.deb" 2>/dev/null || true
        if [[ -f "/tmp/${meta}.deb" ]]; then
            cp "/tmp/${meta}.deb" "${LBC}/kali-config/common/packages/"
        fi
        cd "${BUILD_DIR}"
    fi
done

# Create directories
mkdir -p "${INCLUDES}/var/log/aegisnova/"{ai,scans,reports,evidence,incident-response,updates}
mkdir -p "${INCLUDES}/etc/aegisnova/vault" && chmod 700 "${INCLUDES}/etc/aegisnova/vault"
mkdir -p "${INCLUDES}/opt/aegisnova/"{sigma-rules,osint-reports,attack-data}
mkdir -p "${INCLUDES}/etc/aegisnova/"{yubikey,tpm} && chmod 700 "${INCLUDES}/etc/aegisnova/"{yubikey,tpm}
mkdir -p "${INCLUDES}/etc/sysctl.d"
cp "${WIN_PROJ}/overlay/sysctl/99-aegisnova-hardening.conf" "${INCLUDES}/etc/sysctl.d/" 2>/dev/null || true
cp "${WIN_PROJ}/overlay/firewall/nftables.conf" "${INCLUDES}/etc/" 2>/dev/null || true
mkdir -p "${INCLUDES}/etc/ssh/sshd_config.d"
cp "${WIN_PROJ}/overlay/ssh/aegisnova-hardened.conf" "${INCLUDES}/etc/ssh/sshd_config.d/" 2>/dev/null || true
mkdir -p "${INCLUDES}/etc/skel/.config/autostart"
cp "${WIN_PROJ}/overlay/autostart/"*.desktop "${INCLUDES}/etc/skel/.config/autostart/" 2>/dev/null || true
cp "${WIN_PROJ}/LEGAL_NOTICE.md" "${INCLUDES}/etc/aegisnova/" 2>/dev/null || true

# Copy theme
mkdir -p "${INCLUDES}/usr/share/backgrounds/aegisnova"
cp "${WIN_PROJ}/overlay/theme/wallpapers/"*.{jpg,png,svg} "${INCLUDES}/usr/share/backgrounds/aegisnova/" 2>/dev/null || true
mkdir -p "${INCLUDES}/opt/aegisnova/theme"
cp "${WIN_PROJ}/overlay/theme/install-macos-theme.sh" "${INCLUDES}/opt/aegisnova/theme/" 2>/dev/null || true
cp "${WIN_PROJ}/overlay/theme/macos-theme.conf" "${INCLUDES}/etc/aegisnova/" 2>/dev/null || true

# Copy docker compose
mkdir -p "${INCLUDES}/opt/aegisnova/docker"
cp "${WIN_PROJ}/overlay/docker/"*.yml "${INCLUDES}/opt/aegisnova/docker/" 2>/dev/null || true

# 3. Build ISO on ext4
log "Starting live-build on ext4 ..."
cd "${LBC}"
./build.sh --verbose --arch amd64 --distribution kali-rolling 2>&1 | tee "${BUILD_DIR}/iso-build.log"

# 4. Move ISO back to Windows
ISO_NAME="kali-linux-$(grep -oP '(?<=KALI_VERSION=)kali-rolling' .getopt.sh >/dev/null 2>&1 && echo 'rolling' || echo '*')-live-amd64.iso"
BUILT_ISO=$(ls -t images/*.iso 2>/dev/null | head -1)
if [[ -n "${BUILT_ISO}" ]]; then
    log "✅ ISO built: ${BUILT_ISO}"
    mv "${BUILT_ISO}" "${WIN_PROJ}/AegisNova-v1.0.iso"
    log "Moved to: ${WIN_PROJ}/AegisNova-v1.0.iso"
    log "Size: $(du -sh "${WIN_PROJ}/AegisNova-v1.0.iso" | cut -f1)"
else
    err "ISO not found! Check ${BUILD_DIR}/iso-build.log"
fi

# Cleanup
rm -rf "${BUILD_DIR}"
log "✅ ALL DONE!"
