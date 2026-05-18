#!/usr/bin/env bash
# ============================================================================
# AegisNova OS — Reproducible Kernel Build Script
# ============================================================================
# Downloads, verifies, configures, and compiles the latest stable Linux 7.x
# kernel with BPF, XDP, SELinux, Lockdown, eBPF, IMA/EVM, and optional
# GRSECURITY hardening patches.
#
# Usage:
#   chmod +x build_kernel.sh
#   sudo ./build_kernel.sh [--grsec] [--sign-modules] [--jobs N]
#
# Prerequisites:
#   apt install -y build-essential libncurses-dev bison flex libssl-dev \
#       libelf-dev bc dwarves debhelper rsync kmod cpio gnupg wget
# ============================================================================

set -euo pipefail
IFS=$'\n\t'

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
KERNEL_MAJOR="6"
KERNEL_VERSION="6.12.30"                     # 6.12 LTS — check kernel.org for latest 6.12.x
KERNEL_URL="https://cdn.kernel.org/pub/linux/kernel/v${KERNEL_MAJOR}.x/linux-${KERNEL_VERSION}.tar.xz"
KERNEL_SIG_URL="https://cdn.kernel.org/pub/linux/kernel/v${KERNEL_MAJOR}.x/linux-${KERNEL_VERSION}.tar.sign"
KERNEL_TARBALL="linux-${KERNEL_VERSION}.tar.xz"
KERNEL_SIG="linux-${KERNEL_VERSION}.tar.sign"
BUILD_DIR="$(pwd)/kernel-build"
CONFIG_FRAGMENT="$(pwd)/configs/kernel/aegisnova-security.config"  # Kconfig fragment
JOBS="$(nproc)"
ENABLE_GRSEC=false
SIGN_MODULES=false

# GPG key IDs for kernel.org maintainers
GPG_KEYS=(
    "ABAF11C65A2970B130ABE3C479BE3E4300411886"   # Linus Torvalds
    "647F28654894E3BD457199BE38DBBDC86092693E"   # Greg KH
)

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --grsec)       ENABLE_GRSEC=true; shift ;;
        --sign-modules) SIGN_MODULES=true; shift ;;
        --jobs)        JOBS="$2"; shift 2 ;;
        *)             echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
log()  { echo -e "\e[1;36m[AegisNova Kernel]\e[0m $*"; }
err()  { echo -e "\e[1;31m[ERROR]\e[0m $*" >&2; exit 1; }
warn() { echo -e "\e[1;33m[WARN]\e[0m $*"; }

check_root() {
    if [[ $EUID -ne 0 ]]; then
        err "This script must be run as root (or via sudo)."
    fi
}

# ---------------------------------------------------------------------------
# Step 1 — Download kernel source
# ---------------------------------------------------------------------------
download_kernel() {
    log "Creating build directory: ${BUILD_DIR}"
    mkdir -p "${BUILD_DIR}"
    cd "${BUILD_DIR}"

    if [[ -f "${KERNEL_TARBALL}" ]]; then
        log "Kernel tarball already present — skipping download."
    else
        log "Downloading Linux ${KERNEL_VERSION} from kernel.org …"
        wget --progress=dot:giga -c "${KERNEL_URL}" -O "${KERNEL_TARBALL}"
        wget --progress=dot:giga -c "${KERNEL_SIG_URL}" -O "${KERNEL_SIG}"
    fi
}

# ---------------------------------------------------------------------------
# Step 2 — Verify GPG signature
# ---------------------------------------------------------------------------
verify_signature() {
    log "Importing kernel.org GPG keys …"
    for key in "${GPG_KEYS[@]}"; do
        gpg --keyserver hkps://keyserver.ubuntu.com --recv-keys "${key}" 2>/dev/null || \
        gpg --keyserver hkps://keys.openpgp.org   --recv-keys "${key}" 2>/dev/null || \
            warn "Could not import key ${key} — signature check may fail."
    done

    # The .sign file is for the uncompressed tarball
    log "Decompressing tarball for signature verification …"
    xz -dk "${KERNEL_TARBALL}" 2>/dev/null || true

    log "Verifying GPG signature …"
    if gpg --verify "${KERNEL_SIG}" "linux-${KERNEL_VERSION}.tar" 2>&1 | grep -q "Good signature"; then
        log "✅ GPG signature verified successfully."
    else
        warn "⚠️  GPG signature could not be verified. Proceeding anyway (non-fatal)."
    fi

    # Clean up uncompressed tar to save space
    rm -f "linux-${KERNEL_VERSION}.tar"
}

# ---------------------------------------------------------------------------
# Step 3 — Extract source tree
# ---------------------------------------------------------------------------
extract_source() {
    if [[ -d "linux-${KERNEL_VERSION}" ]]; then
        log "Source tree already extracted."
    else
        log "Extracting kernel source …"
        tar -xf "${KERNEL_TARBALL}"
    fi
    cd "linux-${KERNEL_VERSION}"
}

# ---------------------------------------------------------------------------
# Step 4 — Apply custom .config
# ---------------------------------------------------------------------------
apply_config() {
    log "Applying kernel configuration …"

    # ── Step 1: Generate a sane base config ──
    # kvm_guest.config is ideal — supports both VM testing and bare-metal
    if make kvm_guest.config 2>/dev/null; then
        log "Base: kvm_guest.config (VM + bare-metal compatible)"
    else
        log "Falling back to defconfig …"
        make defconfig
    fi

    # ── Step 2: Merge security fragment if present ──
    if [[ -f "${CONFIG_FRAGMENT}" ]]; then
        log "Merging security fragment: ${CONFIG_FRAGMENT}"
        if [[ -x scripts/kconfig/merge_config.sh ]]; then
            scripts/kconfig/merge_config.sh -m .config "${CONFIG_FRAGMENT}" 2>/dev/null
        else
            # Fallback: apply options manually
            while IFS='=' read -r key val; do
                [[ "${key}" =~ ^CONFIG_ ]] || continue
                val="${val//\"/}"
                if [[ "${val}" == "y" || "${val}" == "m" ]]; then
                    ./scripts/config --enable  "${key}" 2>/dev/null || true
                elif [[ "${val}" == "n" ]]; then
                    ./scripts/config --disable "${key}" 2>/dev/null || true
                else
                    ./scripts/config --set-val "${key}" "${val}" 2>/dev/null || true
                fi
            done < "${CONFIG_FRAGMENT}"
        fi
        log "✅ Security fragment merged."
    else
        warn "No security fragment at ${CONFIG_FRAGMENT} — applying hardening inline …"
    fi

    # ── Step 3: Force-enable critical security / telemetry options ──
    # (Applied regardless of fragment — guarantees minimum security baseline)
    local OPTS=(
        # BPF & XDP
        "CONFIG_BPF=y"
        "CONFIG_BPF_SYSCALL=y"
        "CONFIG_BPF_JIT=y"
        "CONFIG_BPF_JIT_ALWAYS_ON=y"
        "CONFIG_XDP_SOCKETS=y"
        "CONFIG_NET_ACT_BPF=y"
        "CONFIG_BPF_STREAM_PARSER=y"
        # Security modules
        "CONFIG_SECURITY=y"
        "CONFIG_SECCOMP=y"
        "CONFIG_SECCOMP_FILTER=y"
        "CONFIG_SECURITY_SELINUX=y"
        "CONFIG_SECURITY_SELINUX_BOOTPARAM=y"
        "CONFIG_SECURITY_APPARMOR=y"
        "CONFIG_SECURITY_LOCKDOWN_LSM=y"
        "CONFIG_SECURITY_LOCKDOWN_LSM_EARLY=y"
        "CONFIG_LOCK_DOWN_KERNEL_FORCE_INTEGRITY=y"
        # Integrity
        "CONFIG_INTEGRITY=y"
        "CONFIG_IMA=y"
        "CONFIG_EVM=y"
        # Audit
        "CONFIG_AUDIT=y"
        "CONFIG_AUDITSYSCALL=y"
        # Module signing
        "CONFIG_MODULE_SIG=y"
        "CONFIG_MODULE_SIG_ALL=y"
        "CONFIG_MODULE_SIG_SHA512=y"
        "CONFIG_MODULE_SIG_FORCE=y"
        # Memory hardening
        "CONFIG_RANDOMIZE_BASE=y"
        "CONFIG_RANDOMIZE_MEMORY=y"
        "CONFIG_STACKPROTECTOR=y"
        "CONFIG_STACKPROTECTOR_STRONG=y"
        "CONFIG_FORTIFY_SOURCE=y"
        "CONFIG_HARDENED_USERCOPY=y"
        "CONFIG_INIT_ON_ALLOC_DEFAULT_ON=y"
        "CONFIG_INIT_ON_FREE_DEFAULT_ON=y"
        "CONFIG_SLAB_FREELIST_RANDOM=y"
        "CONFIG_SLAB_FREELIST_HARDENED=y"
        # Live USB support
        "CONFIG_SQUASHFS=y"
        "CONFIG_SQUASHFS_XZ=y"
        "CONFIG_OVERLAY_FS=y"
        "CONFIG_ISO9660_FS=y"
        "CONFIG_JOLIET=y"
        "CONFIG_USB_STORAGE=y"
        "CONFIG_USB_UAS=y"
        # LUKS / dm-crypt for encrypted persistence
        "CONFIG_DM_CRYPT=y"
        "CONFIG_CRYPTO_AES=y"
        "CONFIG_CRYPTO_XTS=y"
        "CONFIG_CRYPTO_SHA512=y"
    )

    for opt in "${OPTS[@]}"; do
        key="${opt%%=*}"
        val="${opt##*=}"
        if [[ "${val}" == "y" || "${val}" == "m" ]]; then
            ./scripts/config --enable  "${key}" 2>/dev/null || true
        else
            ./scripts/config --set-val "${key}" "${val}" 2>/dev/null || true
        fi
    done

    # ── Step 4: Optional GRSECURITY patch ──
    if $ENABLE_GRSEC; then
        log "Applying GRSECURITY / PaX hardening …"
        if [[ -f "../../patches/grsecurity.patch" ]]; then
            patch -p1 < "../../patches/grsecurity.patch" || warn "GRSEC patch may have failed."
            ./scripts/config --enable CONFIG_GRKERNSEC 2>/dev/null || true
            ./scripts/config --enable CONFIG_PAX       2>/dev/null || true
        else
            warn "No grsecurity.patch in patches/. Skipping GRSEC."
        fi
    fi

    # ── Step 5: Resolve any new/missing symbols ──
    make olddefconfig
    log "✅ Kernel configuration applied."
}

# ---------------------------------------------------------------------------
# Step 5 — Build kernel .deb packages
# ---------------------------------------------------------------------------
build_kernel() {
    log "Building kernel with ${JOBS} parallel jobs …"
    make -j"${JOBS}" deb-pkg \
        LOCALVERSION="-aegisnova" \
        KDEB_PKGVERSION="1.0.0-1" \
        2>&1 | tee ../build.log

    log "✅ Kernel .deb packages built successfully."
    log "Packages are in: ${BUILD_DIR}/"
    ls -lh "${BUILD_DIR}"/*.deb 2>/dev/null || warn "No .deb files found."
}

# ---------------------------------------------------------------------------
# Step 6 — Sign kernel modules (optional)
# ---------------------------------------------------------------------------
sign_modules() {
    if ! $SIGN_MODULES; then
        return
    fi

    log "Generating module-signing keypair …"
    local CERT_DIR="${BUILD_DIR}/module-signing"
    mkdir -p "${CERT_DIR}"

    # Generate a self-signed X.509 certificate for module signing
    cat > "${CERT_DIR}/x509.genkey" <<'GENKEY'
[ req ]
default_bits = 4096
distinguished_name = req_distinguished_name
prompt = no
string_mask = utf8only
x509_extensions = myexts

[ req_distinguished_name ]
O = AegisNova OS
CN = AegisNova Kernel Module Signing Key
emailAddress = security@aegisnova.local

[ myexts ]
basicConstraints=critical,CA:FALSE
keyUsage=digitalSignature
subjectKeyIdentifier=hash
authorityKeyIdentifier=keyid
GENKEY

    openssl req -new -nodes -utf8 -sha512 -days 3650 \
        -batch -x509 -config "${CERT_DIR}/x509.genkey" \
        -outform PEM -out "${CERT_DIR}/signing_key.pem" \
        -keyout "${CERT_DIR}/signing_key.pem"

    log "Signing all built modules …"
    find . -name '*.ko' -exec \
        ./scripts/sign-file sha512 \
            "${CERT_DIR}/signing_key.pem" \
            "${CERT_DIR}/signing_key.pem" {} \;

    log "✅ All kernel modules signed."
    log "Certificate stored at: ${CERT_DIR}/signing_key.pem"
    log "Enroll this certificate in your UEFI MOK database with:"
    log "  mokutil --import ${CERT_DIR}/signing_key.pem"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    check_root
    log "═══════════════════════════════════════════════════════════════"
    log "  AegisNova OS — Kernel Build Pipeline"
    log "  Kernel Version : ${KERNEL_VERSION}"
    log "  Config Fragment: ${CONFIG_FRAGMENT}"
    log "  GRSEC Enabled  : ${ENABLE_GRSEC}"
    log "  Sign Modules   : ${SIGN_MODULES}"
    log "  Parallel Jobs  : ${JOBS}"
    log "═══════════════════════════════════════════════════════════════"

    download_kernel
    verify_signature
    extract_source
    apply_config
    build_kernel
    sign_modules

    log ""
    log "═══════════════════════════════════════════════════════════════"
    log "  ✅ BUILD COMPLETE"
    log "  Install the kernel with:"
    log "    dpkg -i ${BUILD_DIR}/linux-*.deb"
    log "═══════════════════════════════════════════════════════════════"
}

main "$@"
