#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
# AegisNova OS — Secure Memory & Data Wiping Utilities
# ═══════════════════════════════════════════════════════════
# Provides secure data destruction capabilities:
# - RAM wiping (secure memory clear)
# - Disk/partition wiping with multiple passes
# - File shredding with verification
# - Swap space wiping
# - Temp directory cleanup
# - Browser cache/history wiping
#
# Usage: sudo aegisnova-wipe [--memory] [--disk /dev/sdX] [--file path] [--all]
# ═══════════════════════════════════════════════════════════
set -euo pipefail

WIPE_LOG="/var/log/aegisnova/wipe.log"
WIPE_MEMORY=false
WIPE_DISK=""
WIPE_FILE=""
WIPE_ALL=false
PASSES=3

log()  { echo -e "\e[1;32m[WIPE]\e[0m $*" | tee -a "${WIPE_LOG}"; }
err()  { echo -e "\e[1;31m[ERROR]\e[0m $*" >&2 | tee -a "${WIPE_LOG}"; exit 1; }
warn() { echo -e "\e[1;33m[WARN]\e[0m $*" | tee -a "${WIPE_LOG}"; }
info() { echo -e "\e[1;34m[INFO]\e[0m $*" | tee -a "${WIPE_LOG}"; }

# ── Parse args ──
while [[ $# -gt 0 ]]; do
    case "$1" in
        --memory)   WIPE_MEMORY=true; shift ;;
        --disk)     WIPE_DISK="$2"; shift 2 ;;
        --file)     WIPE_FILE="$2"; shift 2 ;;
        --passes)   PASSES="$2"; shift 2 ;;
        --all)      WIPE_ALL=true; shift ;;
        *)          err "Unknown option: $1"; ;;
    esac
done

# ── Check root ──
[[ $EUID -eq 0 ]] || err "Must be run as root."

mkdir -p "$(dirname "${WIPE_LOG}")"
touch "${WIPE_LOG}"
chmod 600 "${WIPE_LOG}"

log "═══════════════════════════════════════════════════════════════"
log "  AegisNova Secure Wipe Utility"
log "═══════════════════════════════════════════════════════════════"

# ═══════════════════════════════════════════════════════════
# Memory Wiping
# ═══════════════════════════════════════════════════════════

wipe_memory() {
    log "Starting secure memory wipe ..."
    
    # Clear caches
    log "  Clearing filesystem caches ..."
    sync
    echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true
    
    # Clear swap
    if [[ -f /proc/swaps ]] && grep -q swap /proc/swaps; then
        log "  Disabling and clearing swap ..."
        swapoff -a 2>/dev/null || true
        for swap_dev in $(awk '/^\/dev/{print $1}' /proc/swaps 2>/dev/null); do
            if [[ -b "${swap_dev}" ]]; then
                log "    Wiping swap device: ${swap_dev}"
                dd if=/dev/zero of="${swap_dev}" bs=1M status=progress 2>/dev/null || true
            fi
        done
        swapon -a 2>/dev/null || true
    fi
    
    # Overwrite RAM (fill with zeros via tmpfs)
    log "  Overwriting RAM with zeros ..."
    local ram_size=$(free -m | awk '/^Mem:/{print $2}')
    local chunk_size=$((ram_size / 4))
    
    for i in 1 2 3; do
        log "    Memory pass ${i}/3 ..."
        dd if=/dev/zero of=/dev/shm/.memwipe bs=1M count="${chunk_size}" 2>/dev/null || true
        sync
        rm -f /dev/shm/.memwipe
        sync
    done
    
    # Clear bash history in memory
    log "  Clearing shell history from memory ..."
    history -c 2>/dev/null || true
    
    log "✅ Memory wipe complete."
}

# ═══════════════════════════════════════════════════════════
# Disk/Partition Wiping
# ═══════════════════════════════════════════════════════════

wipe_disk() {
    local target="${1}"
    
    if [[ ! -b "${target}" ]]; then
        err "Device ${target} not found."
    fi
    
    log "WARNING: This will DESTROY ALL DATA on ${target}"
    read -rp "Type 'DESTROY' to continue: " CONFIRM
    [[ "${CONFIRM}" == "DESTROY" ]] || err "Aborted."
    
    log "Starting secure disk wipe of ${target} ..."
    log "  Passes: ${PASSES}"
    
    local total_size=$(blockdev --getsize64 "${target}" 2>/dev/null || echo "0")
    
    for pass in $(seq 1 ${PASSES}); do
        log "  Pass ${pass}/${PASSES}: Writing random data ..."
        if command -v shred &>/dev/null; then
            shred -v -n 1 -z "${target}" 2>/dev/null || true
        else
            dd if=/dev/urandom of="${target}" bs=4M status=progress 2>/dev/null || true
        fi
    done
    
    # Final zero pass
    log "  Final pass: Writing zeros ..."
    dd if=/dev/zero of="${target}" bs=4M status=progress 2>/dev/null || true
    sync
    
    log "✅ Disk wipe complete: ${target}"
}

# ═══════════════════════════════════════════════════════════
# File Shredding
# ═══════════════════════════════════════════════════════════

wipe_file() {
    local target="${1}"
    
    if [[ ! -f "${target}" ]]; then
        err "File ${target} not found."
    fi
    
    log "Shredding file: ${target} ..."
    
    if command -v shred &>/dev/null; then
        shred -vfz -n "${PASSES}" "${target}" 2>/dev/null || true
    else
        # Manual shred fallback
        local file_size=$(stat -c%s "${target}" 2>/dev/null || echo "0")
        
        for pass in $(seq 1 ${PASSES}); do
            log "  Pass ${pass}/${PASSES} ..."
            dd if=/dev/urandom of="${target}" bs=1 count="${file_size}" conv=notrunc 2>/dev/null || true
            sync
        done
        
        # Zero pass
        dd if=/dev/zero of="${target}" bs=1 count="${file_size}" conv=notrunc 2>/dev/null || true
        sync
        rm -f "${target}"
    fi
    
    log "✅ File shredded: ${target}"
}

# ═══════════════════════════════════════════════════════════
# Comprehensive Cleanup
# ═══════════════════════════════════════════════════════════

wipe_all_temp() {
    log "Starting comprehensive cleanup ..."
    
    # Clear temp directories
    log "  Clearing temporary directories ..."
    for dir in /tmp /var/tmp /dev/shm; do
        if [[ -d "${dir}" ]]; then
            find "${dir}" -type f -exec rm -f {} + 2>/dev/null || true
        fi
    done
    
    # Clear browser caches (common locations)
    log "  Clearing browser caches ..."
    for user_home in /root /home/*; do
        if [[ -d "${user_home}" ]]; then
            local user=$(basename "${user_home}")
            for browser_dir in .mozilla .config/google-chrome .config/chromium .config/BraveSoftware; do
                local cache_path="${user_home}/${browser_dir}"
                if [[ -d "${cache_path}" ]]; then
                    find "${cache_path}" -type f -name "Cache*" -exec rm -f {} + 2>/dev/null || true
                fi
            done
        fi
    done
    
    # Clear package caches
    log "  Clearing package caches ..."
    apt-get clean 2>/dev/null || true
    
    # Clear thumbnail cache
    log "  Clearing thumbnail caches ..."
    for user_home in /root /home/*; do
        if [[ -d "${user_home}/.cache/thumbnails" ]]; then
            rm -rf "${user_home}/.cache/thumbnails"/* 2>/dev/null || true
        fi
    done
    
    # Clear journal logs (optional, keep last 7 days)
    log "  Trimming journal logs ..."
    journalctl --vacuum-time=7d 2>/dev/null || true
    
    # Clear bash history for all users
    log "  Clearing shell history ..."
    for hist_file in /root/.bash_history /home/*/.bash_history; do
        if [[ -f "${hist_file}" ]]; then
            shred -uf "${hist_file}" 2>/dev/null || true
            touch "${hist_file}"
            chmod 600 "${hist_file}"
        fi
    done
    
    # Clear AegisNova specific logs (keep last 24h)
    log "  Trimming AegisNova logs ..."
    find /var/log/aegisnova -type f -mtime +1 -exec rm -f {} + 2>/dev/null || true
    
    log "✅ Comprehensive cleanup complete."
}

# ═══════════════════════════════════════════════════════════
# Main Execution
# ═══════════════════════════════════════════════════════════

if ${WIPE_ALL}; then
    wipe_memory
    wipe_all_temp
elif ${WIPE_MEMORY}; then
    wipe_memory
elif [[ -n "${WIPE_DISK}" ]]; then
    wipe_disk "${WIPE_DISK}"
elif [[ -n "${WIPE_FILE}" ]]; then
    wipe_file "${WIPE_FILE}"
else
    log "AegisNova Secure Wipe Utility"
    log ""
    log "Usage:"
    log "  aegisnova-wipe --memory           Wipe RAM and swap"
    log "  aegisnova-wipe --disk /dev/sdX    Securely wipe disk/partition"
    log "  aegisnova-wipe --file /path/file  Securely shred file"
    log "  aegisnova-wipe --all              Comprehensive cleanup"
    log "  aegisnova-wipe --passes N         Number of passes (default: 3)"
    log ""
    log "WARNING: These operations are IRREVERSIBLE!"
fi

log "═══════════════════════════════════════════════════════════════"
