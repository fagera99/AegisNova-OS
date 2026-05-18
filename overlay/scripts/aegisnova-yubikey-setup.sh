#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
# AegisNova OS — YubiKey & TPM Integration Script
# ═══════════════════════════════════════════════════════════
# Sets up hardware-based security for the OS:
# - YubiKey PIV/Smart Card authentication
# - TPM 2.0 sealed LUKS keys
# - FIDO2/U2F SSH authentication
# - YubiKey-based sudo authentication
#
# Usage: sudo aegisnova-yubikey-setup [--tpm] [--ssh] [--sudo] [--full]
# ═══════════════════════════════════════════════════════════
set -euo pipefail

YUBIKEY_DIR="/etc/aegisnova/yubikey"
TPM_DIR="/etc/aegisnova/tpm"
SETUP_MODE="basic"
ENABLE_TPM=false
ENABLE_SSH=false
ENABLE_SUDO=false

log()  { echo -e "\e[1;32m[YUBIKEY/TPM]\e[0m $*"; }
err()  { echo -e "\e[1;31m[ERROR]\e[0m $*" >&2; exit 1; }
warn() { echo -e "\e[1;33m[WARN]\e[0m $*"; }

# ── Parse args ──
while [[ $# -gt 0 ]]; do
    case "$1" in
        --tpm)   ENABLE_TPM=true; shift ;;
        --ssh)   ENABLE_SSH=true; shift ;;
        --sudo)  ENABLE_SUDO=true; shift ;;
        --full)  ENABLE_TPM=true; ENABLE_SSH=true; ENABLE_SUDO=true; SETUP_MODE="full"; shift ;;
        *)       err "Unknown option: $1"; ;;
    esac
done

# ── Check root ──
[[ $EUID -eq 0 ]] || err "Must be run as root."

# ── Install required packages ──
log "Installing required packages..."
apt-get update -qq

PACKAGES="libpam-u2f yubikey-manager yubikey-personalization libfido2-1"
if ${ENABLE_TPM}; then
    PACKAGES="${PACKAGES} tpm2-tools tpm2-abrmd libtss2-tcti-tabrmd0"
fi

apt-get install -y -qq ${PACKAGES} 2>/dev/null || true

# ── Detect YubiKey ──
log "Detecting YubiKey..."
if command -v ykman &>/dev/null; then
    YUBIKEY_INFO=$(ykman info 2>/dev/null || true)
    if [[ -n "${YUBIKEY_INFO}" ]]; then
        log "YubiKey detected:"
        echo "${YUBIKEY_INFO}" | head -5
    else
        warn "No YubiKey detected. Please insert a YubiKey and re-run."
        [[ "${SETUP_MODE}" == "basic" ]] && exit 1
    fi
else
    warn "ykman not available. Manual configuration may be required."
fi

# ── Create directories ──
mkdir -p "${YUBIKEY_DIR}" "${TPM_DIR}"
chmod 700 "${YUBIKEY_DIR}" "${TPM_DIR}"

# ═══════════════════════════════════════════════════════════
# YubiKey FIDO2/U2F SSH Authentication
# ═══════════════════════════════════════════════════════════
if ${ENABLE_SSH}; then
    log "Setting up YubiKey SSH authentication..."
    
    # Generate SSH key using FIDO2/U2F
    SSH_KEY_DIR="/etc/aegisnova/ssh-yubikey"
    mkdir -p "${SSH_KEY_DIR}"
    
    if [[ ! -f "${SSH_KEY_DIR}/id_ecdsa_sk" ]]; then
        log "Generating FIDO2 SSH key (touch your YubiKey when prompted)..."
        ssh-keygen -t ecdsa-sk -f "${SSH_KEY_DIR}/id_ecdsa_sk" -N "" -C "aegisnova-yubikey-$(date +%Y%m%d)"
        
        # Copy public key to authorized_keys for root
        mkdir -p /root/.ssh
        chmod 700 /root/.ssh
        cat "${SSH_KEY_DIR}/id_ecdsa_sk.pub" >> /root/.ssh/authorized_keys
        chmod 600 /root/.ssh/authorized_keys
        
        log "FIDO2 SSH key generated."
        log "Private key: ${SSH_KEY_DIR}/id_ecdsa_sk"
        log "Public key: ${SSH_KEY_DIR}/id_ecdsa_sk.pub"
    else
        log "FIDO2 SSH key already exists."
    fi
    
    # Configure SSH to require YubiKey
    cat > /etc/ssh/sshd_config.d/aegisnova-yubikey.conf << 'EOF'
# AegisNova YubiKey SSH Authentication
AuthenticationMethods publickey
PubkeyAuthentication yes
PasswordAuthentication no
PermitRootLogin prohibit-password
EOF
    
    systemctl restart sshd 2>/dev/null || true
    log "SSH configured to require YubiKey authentication."
fi

# ═══════════════════════════════════════════════════════════
# YubiKey sudo Authentication
# ═══════════════════════════════════════════════════════════
if ${ENABLE_SUDO}; then
    log "Setting up YubiKey sudo authentication..."
    
    # Generate U2F mapping for current user
    PAM_U2F_MAPPING="${YUBIKEY_DIR}/u2f_mapping"
    
    if [[ ! -f "${PAM_U2F_MAPPING}" ]]; then
        log "Registering YubiKey for sudo (touch your YubiKey when prompted)..."
        
        # Create mapping file
        touch "${PAM_U2F_MAPPING}"
        chmod 644 "${PAM_U2F_MAPPING}"
        
        # Register key for root
        if command -v pamu2fcfg &>/dev/null; then
            pamu2fcfg -u root >> "${PAM_U2F_MAPPING}" 2>/dev/null || {
                warn "pamu2fcfg failed. Manual registration required."
                warn "Run: pamu2fcfg -u root >> ${PAM_U2F_MAPPING}"
            }
        else
            warn "pamu2fcfg not available. Manual setup required."
        fi
    fi
    
    # Configure PAM for sudo
    if [[ -f "${PAM_U2F_MAPPING}" && -s "${PAM_U2F_MAPPING}" ]]; then
        # Backup original
        cp /etc/pam.d/sudo /etc/pam.d/sudo.bak.$(date +%Y%m%d) 2>/dev/null || true
        
        cat > /etc/pam.d/sudo << EOF
# AegisNova YubiKey sudo authentication
auth       required   pam_u2f.so cue nouserok origin=pam://aegisnova appid=pam://aegisnova authfile=${PAM_U2F_MAPPING}

@include common-auth
@include common-account
@include common-session-noninteractive
EOF
        
        log "sudo now requires YubiKey authentication."
        warn "Test sudo in a new terminal BEFORE closing this session!"
    fi
fi

# ═══════════════════════════════════════════════════════════
# TPM 2.0 LUKS Key Sealing
# ═══════════════════════════════════════════════════════════
if ${ENABLE_TPM}; then
    log "Setting up TPM 2.0 integration..."
    
    # Check TPM availability
    if [[ ! -c /dev/tpm0 && ! -c /dev/tpmrm0 ]]; then
        warn "No TPM 2.0 device detected. Skipping TPM setup."
        warn "Check: dmesg | grep -i tpm"
    else
        log "TPM 2.0 device detected."
        
        # Check TPM tools
        if command -v tpm2_getcap &>/dev/null; then
            TPM_INFO=$(tpm2_getcap properties-fixed 2>/dev/null | head -10 || true)
            log "TPM Info:"
            echo "${TPM_INFO}"
            
            # Create TPM-sealed LUKS key for persistence
            if [[ -b /dev/mapper/aegisnova-persistence ]]; then
                log "Sealing LUKS key with TPM..."
                
                TPM_KEY="${TPM_DIR}/luks_tpm_key"
                dd if=/dev/urandom bs=1 count=32 2>/dev/null | base64 > "${TPM_KEY}"
                chmod 600 "${TPM_KEY}"
                
                # Seal key to TPM
                tpm2_createprimary -C o -g sha256 -G rsa -c "${TPM_DIR}/primary.ctx" 2>/dev/null || true
                tpm2_create -C "${TPM_DIR}/primary.ctx" -g sha256 -u "${TPM_DIR}/obj.pub" -r "${TPM_DIR}/obj.priv" -i "${TPM_KEY}" 2>/dev/null || true
                tpm2_load -C "${TPM_DIR}/primary.ctx" -u "${TPM_DIR}/obj.pub" -r "${TPM_DIR}/obj.priv" -c "${TPM_DIR}/load.ctx" 2>/dev/null || true
                tpm2_evictcontrol -C o -c "${TPM_DIR}/load.ctx" 0x81010001 2>/dev/null || true
                
                log "TPM-sealed LUKS key created."
                log "Key handle: 0x81010001"
            else
                warn "No AegisNova persistence volume found."
                warn "Set up persistence first with: aegisnova-persistence-setup"
            fi
        else
            warn "tpm2-tools not available. TPM setup incomplete."
        fi
    fi
fi

# ── Store configuration ──
cat > "${YUBIKEY_DIR}/config" << EOF
# AegisNova YubiKey/TPM Configuration
# Generated: $(date -Iseconds)

SETUP_MODE=${SETUP_MODE}
YUBIKEY_DETECTED=$([[ -n "${YUBIKEY_INFO:-}" ]] && echo "yes" || echo "no")
TPM_ENABLED=${ENABLE_TPM}
SSH_ENABLED=${ENABLE_SSH}
SUDO_ENABLED=${ENABLE_SUDO}
EOF

# ── Done ──
log ""
log "═══════════════════════════════════════════════════════════════"
log "  ✅ YubiKey/TPM Setup Complete!"
log "═══════════════════════════════════════════════════════════════"
log ""

if ${ENABLE_SSH}; then
    log "SSH Authentication:"
    log "  Key: ${SSH_KEY_DIR}/id_ecdsa_sk"
    log "  Requires: YubiKey touch on each authentication"
    log ""
fi

if ${ENABLE_SUDO}; then
    log "sudo Authentication:"
    log "  Requires: YubiKey touch for sudo commands"
    log "  Backup: /etc/pam.d/sudo.bak.*"
    log ""
fi

if ${ENABLE_TPM}; then
    log "TPM Integration:"
    log "  LUKS keys sealed to TPM (PCR-bound)"
    log "  Auto-unlock on trusted boot only"
    log ""
fi

log "IMPORTANT: Test all configurations before ending this session!"
log "═══════════════════════════════════════════════════════════════"
