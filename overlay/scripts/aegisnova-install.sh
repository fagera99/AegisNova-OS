#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
# AegisNova OS — Disk Installer
# ═══════════════════════════════════════════════════════════
# Installs the running Live system to disk.
# Can install to entire disk or alongside existing OS.
#
# Usage (from Live USB): sudo aegisnova-install [--disk /dev/sdX] [--encrypt]
# ═══════════════════════════════════════════════════════════
set -euo pipefail

INSTALL_LOG="/var/log/aegisnova/install.log"
TARGET_DISK=""
ENCRYPT_DISK=false
HOSTNAME="aegisnova"
USERNAME="aegisnova"

log()  { echo -e "\e[1;32m[INSTALL]\e[0m $*" | tee -a "${INSTALL_LOG}"; }
err()  { echo -e "\e[1;31m[ERROR]\e[0m $*" >&2 | tee -a "${INSTALL_LOG}"; exit 1; }
warn() { echo -e "\e[1;33m[WARN]\e[0m $*" | tee -a "${INSTALL_LOG}"; }
info() { echo -e "\e[1;34m[INFO]\e[0m $*" | tee -a "${INSTALL_LOG}"; }

# ── Parse args ──
while [[ $# -gt 0 ]]; do
    case "$1" in
        --disk)     TARGET_DISK="$2"; shift 2 ;;
        --encrypt)  ENCRYPT_DISK=true; shift ;;
        --hostname) HOSTNAME="$2"; shift 2 ;;
        --username) USERNAME="$2"; shift 2 ;;
        *)          err "Unknown option: $1"; ;;
    esac
done

# ── Check if running live ──
if [[ ! -d /lib/live/mount/medium ]] && [[ ! -f /run/live/medium/.disk/info ]]; then
    warn "This installer is designed to run from the AegisNova Live environment."
    read -rp "Continue anyway? [y/N]: " CONFIRM
    [[ "${CONFIRM}" =~ ^[Yy]$ ]] || err "Aborted."
fi

# ── Check root ──
[[ $EUID -eq 0 ]] || err "Must be run as root."

mkdir -p "$(dirname "${INSTALL_LOG}")"
touch "${INSTALL_LOG}"

log "═══════════════════════════════════════════════════════════════"
log "  AegisNova OS — Disk Installer"
log "═══════════════════════════════════════════════════════════════"

# ── Select disk if not specified ──
if [[ -z "${TARGET_DISK}" ]]; then
    echo ""
    echo "Available disks:"
    lsblk -d -o NAME,SIZE,TYPE,MODEL | grep disk
    echo ""
    read -rp "Enter target disk (e.g., /dev/sda): " TARGET_DISK
fi

[[ -b "${TARGET_DISK}" ]] || err "Disk ${TARGET_DISK} not found."

# Get disk size for validation
DISK_SIZE=$(blockdev --getsize64 "${TARGET_DISK}" 2>/dev/null || echo "0")
DISK_GB=$((DISK_SIZE / 1024 / 1024 / 1024))

if [[ ${DISK_GB} -lt 32 ]]; then
    err "Disk too small. Minimum 32GB required (have: ${DISK_GB}GB)."
fi

# ── Safety warning ──
log "WARNING: All data on ${TARGET_DISK} will be DESTROYED!"
log "Disk: ${TARGET_DISK} (${DISK_GB}GB)"
log "Encryption: ${ENCRYPT_DISK}"
log "Hostname: ${HOSTNAME}"
log "Username: ${USERNAME}"
echo ""
read -rp "Type 'INSTALL' to proceed: " CONFIRM
[[ "${CONFIRM}" == "INSTALL" ]] || err "Aborted."

# ── Unmount existing partitions ──
log "Unmounting existing partitions ..."
umount "${TARGET_DISK}"* 2>/dev/null || true
swapoff "${TARGET_DISK}"* 2>/dev/null || true

# ═══════════════════════════════════════════════════════════
# Partitioning
# ═══════════════════════════════════════════════════════════

log "Creating partition table ..."

if ${ENCRYPT_DISK}; then
    # Encrypted layout: EFI + Boot + LUKS
    log "Partitioning with LUKS encryption ..."
    parted -s "${TARGET_DISK}" mklabel gpt
    parted -s "${TARGET_DISK}" mkpart primary fat32 1MiB 512MiB
    parted -s "${TARGET_DISK}" mkpart primary ext4 512MiB 1024MiB
    parted -s "${TARGET_DISK}" mkpart primary ext4 1024MiB 100%
    parted -s "${TARGET_DISK}" set 1 esp on
    parted -s "${TARGET_DISK}" set 1 boot on
    parted -s "${TARGET_DISK}" name 1 "EFI System"
    parted -s "${TARGET_DISK}" name 2 "Boot"
    parted -s "${TARGET_DISK}" name 3 "AegisNova-Encrypted"
    
    sync
    partprobe "${TARGET_DISK}" 2>/dev/null || true
    sleep 2
    
    EFI_PART="${TARGET_DISK}1"
    BOOT_PART="${TARGET_DISK}2"
    LUKS_PART="${TARGET_DISK}3"
    
    # Setup LUKS
    log "Setting up LUKS encryption (you will set passphrase)..."
    cryptsetup luksFormat "${LUKS_PART}"
    cryptsetup luksOpen "${LUKS_PART}" aegisnova-root
    
    ROOT_DEV="/dev/mapper/aegisnova-root"
    
    log "Creating filesystems ..."
    mkfs.fat -F32 "${EFI_PART}"
    mkfs.ext4 -L "AegisNova-Boot" "${BOOT_PART}"
    mkfs.ext4 -L "AegisNova-Root" "${ROOT_DEV}"
    
    # Create LVM for flexibility (optional)
    # pvcreate "${ROOT_DEV}"
    # vgcreate aegisnova-vg "${ROOT_DEV}"
    # lvcreate -L 20G -n root aegisnova-vg
    # lvcreate -L 4G -n swap aegisnova-vg
    # ROOT_DEV="/dev/aegisnova-vg/root"
    
else
    # Standard layout: EFI + Root + Swap
    log "Partitioning standard layout ..."
    parted -s "${TARGET_DISK}" mklabel gpt
    parted -s "${TARGET_DISK}" mkpart primary fat32 1MiB 512MiB
    parted -s "${TARGET_DISK}" mkpart primary ext4 512MiB 28GiB
    parted -s "${TARGET_DISK}" mkpart primary linux-swap 28GiB 32GiB
    parted -s "${TARGET_DISK}" mkpart primary ext4 32GiB 100%
    parted -s "${TARGET_DISK}" set 1 esp on
    parted -s "${TARGET_DISK}" set 1 boot on
    
    sync
    partprobe "${TARGET_DISK}" 2>/dev/null || true
    sleep 2
    
    EFI_PART="${TARGET_DISK}1"
    ROOT_PART="${TARGET_DISK}2"
    SWAP_PART="${TARGET_DISK}3"
    HOME_PART="${TARGET_DISK}4"
    
    log "Creating filesystems ..."
    mkfs.fat -F32 "${EFI_PART}"
    mkfs.ext4 -L "AegisNova-Root" "${ROOT_PART}"
    mkswap -L "AegisNova-Swap" "${SWAP_PART}"
    mkfs.ext4 -L "AegisNova-Home" "${HOME_PART}"
    
    ROOT_DEV="${ROOT_PART}"
fi

# ═══════════════════════════════════════════════════════════
# Install System
# ═══════════════════════════════════════════════════════════

MOUNT_POINT="/mnt/aegisnova-install"
mkdir -p "${MOUNT_POINT}"

log "Mounting target filesystems ..."
mount "${ROOT_DEV}" "${MOUNT_POINT}"
mkdir -p "${MOUNT_POINT}/boot/efi"
mount "${EFI_PART}" "${MOUNT_POINT}/boot/efi"

if ! ${ENCRYPT_DISK}; then
    mkdir -p "${MOUNT_POINT}/home"
    mount "${HOME_PART}" "${MOUNT_POINT}/home"
fi

# ── Rsync live system ──
log "Copying live system to disk (this may take 10-30 minutes)..."
EXCLUDES="/dev /proc /sys /run /tmp /mnt /media /lost+found /var/cache/apt/archives"
RSYNC_EXCLUDES=""
for ex in ${EXCLUDES}; do
    RSYNC_EXCLUDES="${RSYNC_EXCLUDES} --exclude=${ex}"
done

rsync -aHAXx --progress ${RSYNC_EXCLUDES} / "${MOUNT_POINT}/" 2>&1 | tee -a "${INSTALL_LOG}"

# ── Fixup filesystem ──
log "Configuring installed system ..."

# Create required mount points
mkdir -p "${MOUNT_POINT}"/{dev,proc,sys,run,tmp,mnt,media}

# fstab
cat > "${MOUNT_POINT}/etc/fstab" << EOF
# AegisNova OS fstab
$(blkid -s UUID -o value "${EFI_PART}") /boot/efi vfat defaults,noatime 0 2
$(blkid -s UUID -o value "${ROOT_DEV}") / ext4 defaults,noatime 0 1
EOF

if ! ${ENCRYPT_DISK}; then
    cat >> "${MOUNT_POINT}/etc/fstab" << EOF
$(blkid -s UUID -o value "${HOME_PART}") /home ext4 defaults,noatime 0 2
$(blkid -s UUID -o value "${SWAP_PART}") none swap sw 0 0
EOF
else
    cat >> "${MOUNT_POINT}/etc/fstab" << EOF
/dev/mapper/aegisnova-root / ext4 defaults,noatime 0 1
EOF
fi

# Hostname
echo "${HOSTNAME}" > "${MOUNT_POINT}/etc/hostname"
cat > "${MOUNT_POINT}/etc/hosts" << EOF
127.0.0.1   localhost
127.0.1.1   ${HOSTNAME}
::1         localhost ip6-localhost ip6-loopback
EOF

# Locale
echo "LANG=en_US.UTF-8" > "${MOUNT_POINT}/etc/default/locale"

# ── Install bootloader ──
log "Installing GRUB bootloader ..."
mount --bind /dev "${MOUNT_POINT}/dev"
mount --bind /proc "${MOUNT_POINT}/proc"
mount --bind /sys "${MOUNT_POINT}/sys"
mount --bind /run "${MOUNT_POINT}/run"

# Install GRUB packages
chroot "${MOUNT_POINT}" apt-get update -qq 2>/dev/null || true
chroot "${MOUNT_POINT}" apt-get install -y -qq grub-efi-amd64 grub-pc efibootmgr 2>/dev/null || true

# Install GRUB
chroot "${MOUNT_POINT}" grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=AegisNova --removable 2>/dev/null || \
chroot "${MOUNT_POINT}" grub-install "${TARGET_DISK}" 2>/dev/null || true

# Update GRUB config
if ${ENCRYPT_DISK}; then
    # Add cryptdevice parameter
    sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="/GRUB_CMDLINE_LINUX_DEFAULT="cryptdevice='"${LUKS_PART}"':aegisnova-root /' "${MOUNT_POINT}/etc/default/grub"
    # Enable cryptodisk in GRUB
    echo "GRUB_ENABLE_CRYPTODISK=y" >> "${MOUNT_POINT}/etc/default/grub"
fi

chroot "${MOUNT_POINT}" update-grub 2>/dev/null || true

# Update initramfs for LUKS
if ${ENCRYPT_DISK}; then
    log "Updating initramfs for LUKS..."
    chroot "${MOUNT_POINT}" update-initramfs -u -k all 2>/dev/null || true
fi

# ── Create user ──
log "Creating user: ${USERNAME} ..."
chroot "${MOUNT_POINT}" useradd -m -s /bin/bash -G sudo,adm,audio,video,netdev,docker "${USERNAME}" 2>/dev/null || true
# Set password (will prompt)
log "Set password for ${USERNAME}:"
chroot "${MOUNT_POINT}" passwd "${USERNAME}"

# ── Enable services ──
log "Enabling services ..."
chroot "${MOUNT_POINT}" systemctl enable NetworkManager 2>/dev/null || true
chroot "${MOUNT_POINT}" systemctl enable docker 2>/dev/null || true
chroot "${MOUNT_POINT}" systemctl enable auditd 2>/dev/null || true
chroot "${MOUNT_POINT}" systemctl enable nftables 2>/dev/null || true

# ── Unmount ──
log "Cleaning up ..."
umount "${MOUNT_POINT}/run" 2>/dev/null || true
umount "${MOUNT_POINT}/sys" 2>/dev/null || true
umount "${MOUNT_POINT}/proc" 2>/dev/null || true
umount "${MOUNT_POINT}/dev" 2>/dev/null || true
umount "${MOUNT_POINT}/boot/efi" 2>/dev/null || true
umount "${MOUNT_POINT}/home" 2>/dev/null || true
umount "${MOUNT_POINT}" 2>/dev/null || true

if ${ENCRYPT_DISK}; then
    cryptsetup luksClose aegisnova-root 2>/dev/null || true
fi

# ── Done ──
log ""
log "═══════════════════════════════════════════════════════════════"
log "  ✅ AegisNova OS Installation Complete!"
log "═══════════════════════════════════════════════════════════════"
log ""
log "Installation Details:"
log "  Disk:     ${TARGET_DISK}"
log "  Encrypted: ${ENCRYPT_DISK}"
log "  Hostname: ${HOSTNAME}"
log "  User:     ${USERNAME}"
log ""
log "Next Steps:"
log "  1. Remove USB drive"
log "  2. Reboot: reboot"
log "  3. Boot from ${TARGET_DISK}"
log ""
if ${ENCRYPT_DISK}; then
    log "  NOTE: You will be prompted for LUKS passphrase at boot."
fi
log "═══════════════════════════════════════════════════════════════"
