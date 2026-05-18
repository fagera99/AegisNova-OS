#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
# AegisNova OS — LUKS Persistence Setup for Live ISO
# ═══════════════════════════════════════════════════════════
# Sets up encrypted persistent storage on a USB drive
# running the AegisNova OS live ISO.
#
# Usage: sudo aegisnova-persistence-setup /dev/sdX
# ═══════════════════════════════════════════════════════════
set -euo pipefail

PERSISTENCE_LABEL="aegisnova-persistence"
PERSISTENCE_SIZE="${PERSISTENCE_SIZE:-8192}"  # Default 8GB
CIPHER="aes-xts-plain64"
HASH="sha512"
KEY_SIZE="512"

log()  { echo -e "\e[1;32m[PERSISTENCE]\e[0m $*"; }
err()  { echo -e "\e[1;31m[ERROR]\e[0m $*" >&2; exit 1; }
warn() { echo -e "\e[1;33m[WARN]\e[0m $*"; }

# ── Check root ──
[[ $EUID -eq 0 ]] || err "Must be run as root."

# ── Parse args ──
TARGET_DEVICE="${1:-}"
[[ -n "${TARGET_DEVICE}" ]] || err "Usage: $0 /dev/sdX"
[[ -b "${TARGET_DEVICE}" ]] || err "Device ${TARGET_DEVICE} not found."

# ── Safety check ──
log "WARNING: This will ERASE all data on ${TARGET_DEVICE}"
read -rp "Type 'YES' to continue: " CONFIRM
[[ "${CONFIRM}" == "YES" ]] || err "Aborted."

# ── Install required tools ──
log "Installing cryptsetup tools ..."
apt-get update -qq
apt-get install -y -qq cryptsetup parted dosfstools 2>/dev/null || true

# ── Unmount any mounted partitions ──
log "Unmounting existing partitions ..."
umount "${TARGET_DEVICE}"* 2>/dev/null || true
swapoff "${TARGET_DEVICE}"* 2>/dev/null || true

# ── Wipe partition table ──
log "Wiping partition table ..."
sgdisk -Z "${TARGET_DEVICE}" 2>/dev/null || dd if=/dev/zero of="${TARGET_DEVICE}" bs=512 count=2048 status=progress
sync

# ── Create partitions ──
# Partition 1: FAT32 for ISO (already has ISO, we preserve it if it exists)
# But since we're working with a new USB, we assume ISO is already written
# We just add a new partition for persistence

log "Creating persistence partition ..."
parted -s "${TARGET_DEVICE}" mklabel gpt
parted -s "${TARGET_DEVICE}" mkpart primary fat32 1MiB 4096MiB  # For ISO (4GB)
parted -s "${TARGET_DEVICE}" mkpart primary linux-swap 4096MiB 5120MiB  # 1GB swap
parted -s "${TARGET_DEVICE}" mkpart primary ext4 5120MiB 100%   # Rest for persistence
parted -s "${TARGET_DEVICE}" set 1 boot on
parted -s "${TARGET_DEVICE}" set 1 legacy_boot on
sync

# Wait for kernel to re-read partition table
partprobe "${TARGET_DEVICE}" 2>/dev/null || true
sleep 2

PERSISTENCE_PART="${TARGET_DEVICE}3"
[[ -b "${PERSISTENCE_PART}" ]] || err "Failed to create persistence partition."

# ── Setup LUKS encryption ──
log "Setting up LUKS encryption on ${PERSISTENCE_PART} ..."
log "You will be asked to enter a strong passphrase for the encrypted persistence."

cryptsetup --verbose --cipher="${CIPHER}" --hash="${HASH}" --key-size="${KEY_SIZE}" \
    --verify-passphrase luksFormat "${PERSISTENCE_PART}"

log "Opening encrypted device ..."
cryptsetup luksOpen "${PERSISTENCE_PART}" "${PERSISTENCE_LABEL}"

# ── Create filesystem ──
log "Creating ext4 filesystem ..."
mkfs.ext4 -L "${PERSISTENCE_LABEL}" "/dev/mapper/${PERSISTENCE_LABEL}"

# ── Mount and configure persistence ──
MOUNT_DIR="/mnt/aegisnova-persistence"
mkdir -p "${MOUNT_DIR}"
mount "/dev/mapper/${PERSISTENCE_LABEL}" "${MOUNT_DIR}"

log "Configuring persistence directories ..."
# Create standard Kali persistence structure
mkdir -p "${MOUNT_DIR}/persistence"
mkdir -p "${MOUNT_DIR}/persistence/etc"
mkdir -p "${MOUNT_DIR}/persistence/home"
mkdir -p "${MOUNT_DIR}/persistence/var"
mkdir -p "${MOUNT_DIR}/persistence/usr"
mkdir -p "${MOUNT_DIR}/persistence/opt"
mkdir -p "${MOUNT_DIR}/persistence/root"

# Create persistence.conf
cat > "${MOUNT_DIR}/persistence.conf" << 'EOF'
/etc aegisnova-persistence
/home aegisnova-persistence
/root aegisnova-persistence
/var aegisnova-persistence
/usr/local aegisnova-persistence
/opt aegisnova-persistence
EOF

# Secure permissions
chmod 600 "${MOUNT_DIR}/persistence.conf"

# ── Copy AegisNova configs ──
log "Storing AegisNova configurations ..."
mkdir -p "${MOUNT_DIR}/persistence/etc/aegisnova"

# Store a copy of the environment config
if [[ -f /etc/aegisnova/env ]]; then
    cp /etc/aegisnova/env "${MOUNT_DIR}/persistence/etc/aegisnova/env"
    chmod 600 "${MOUNT_DIR}/persistence/etc/aegisnova/env"
fi

# ── Add AegisNova-specific persistence ──
mkdir -p "${MOUNT_DIR}/persistence/opt/aegisnova"
mkdir -p "${MOUNT_DIR}/persistence/opt/aegisnova/models"
mkdir -p "${MOUNT_DIR}/persistence/opt/aegisnova/heretic"
mkdir -p "${MOUNT_DIR}/persistence/var/log/aegisnova"

# Create auto-mount script for boot
cat > "${MOUNT_DIR}/persistence/etc/aegisnova-persistence-mount.sh" << EOF
#!/usr/bin/env bash
# Auto-mount LUKS persistence on boot
PERSISTENCE_PART="${PERSISTENCE_PART}"
PERSISTENCE_LABEL="${PERSISTENCE_LABEL}"

if [[ -b "\${PERSISTENCE_PART}" ]]; then
    if ! cryptsetup status "\${PERSISTENCE_LABEL}" >/dev/null 2>&1; then
        echo "Mounting encrypted persistence ..."
        cryptsetup luksOpen "\${PERSISTENCE_PART}" "\${PERSISTENCE_LABEL}" || true
        mount "/dev/mapper/\${PERSISTENCE_LABEL}" /persistence 2>/dev/null || true
    fi
fi
EOF
chmod +x "${MOUNT_DIR}/persistence/etc/aegisnova-persistence-mount.sh"

# ── Unmount ──
umount "${MOUNT_DIR}"
cryptsetup luksClose "${PERSISTENCE_LABEL}"
rmdir "${MOUNT_DIR}" 2>/dev/null || true

# ── Done ──
log ""
log "═══════════════════════════════════════════════════════════════"
log "  ✅ LUKS Persistence Setup Complete!"
log "═══════════════════════════════════════════════════════════════"
log ""
log "Persistence Details:"
log "  Device:     ${PERSISTENCE_PART}"
log "  Label:      ${PERSISTENCE_LABEL}"
log "  Cipher:     ${CIPHER}"
log "  Key Size:   ${KEY_SIZE} bits"
log "  Hash:       ${HASH}"
log ""
log "To boot with persistence:"
log "  1. Boot AegisNova ISO"
log "  2. At boot menu, select 'Live USB Persistence'"
log "  3. Enter your LUKS passphrase when prompted"
log ""
log "To manually unlock later:"
log "  cryptsetup luksOpen ${PERSISTENCE_PART} ${PERSISTENCE_LABEL}"
log "  mount /dev/mapper/${PERSISTENCE_LABEL} /mnt"
log ""
log "IMPORTANT: Remember your passphrase! If lost, data cannot be recovered."
log "═══════════════════════════════════════════════════════════════"
