#!/usr/bin/env bash
# ============================================================================
# AegisNova OS — WhiteSur macOS Theme Installer
# ============================================================================
# Installs WhiteSur GTK/GNOME Shell theme, McMojave icons, macOS cursor,
# and SF Pro fonts for the complete macOS look.
# ============================================================================
set -euo pipefail

log() { echo -e "\e[1;36m[Theme Install]\e[0m $*"; }

THEME_DIR="/opt/aegisnova/theme/src"
mkdir -p "${THEME_DIR}"
cd "${THEME_DIR}"

# ── 1. WhiteSur GTK Theme ──
log "Installing WhiteSur GTK theme …"
if [[ ! -d "WhiteSur-gtk-theme" ]]; then
    git clone --depth 1 https://github.com/vinceliuice/WhiteSur-gtk-theme.git
fi
cd WhiteSur-gtk-theme
./install.sh -c Dark -c Light -l --round
cd "${THEME_DIR}"

# ── 2. WhiteSur Icon Theme ──
log "Installing WhiteSur icon theme …"
if [[ ! -d "WhiteSur-icon-theme" ]]; then
    git clone --depth 1 https://github.com/vinceliuice/WhiteSur-icon-theme.git
fi
cd WhiteSur-icon-theme
./install.sh
cd "${THEME_DIR}"

# ── 3. McMojave Circle Icons (alternative) ──
log "Installing McMojave circle icons …"
if [[ ! -d "McMojave-circle" ]]; then
    git clone --depth 1 https://github.com/vinceliuice/McMojave-circle.git
fi
cd McMojave-circle
./install.sh
cd "${THEME_DIR}"

# ── 4. macOS Cursor Theme ──
log "Installing macOS cursor …"
CURSOR_DIR="/usr/share/icons/macOS-cursor"
if [[ ! -d "${CURSOR_DIR}" ]]; then
    if [[ ! -d "apple_cursor" ]]; then
        git clone --depth 1 https://github.com/ful1e5/apple_cursor.git
    fi
    cd apple_cursor
    if [[ -d "dist/macOS-BigSur" ]]; then
        cp -r dist/macOS-BigSur "${CURSOR_DIR}"
    else
        log "Building cursor from source (requires python3, clickgen) …"
        pip3 install clickgen 2>/dev/null || true
        make build 2>/dev/null || log "Cursor build skipped — install manually."
    fi
    cd "${THEME_DIR}"
fi

# ── 5. Fonts ──
log "Installing fonts …"
FONT_DIR="/usr/share/fonts/truetype/sf"
mkdir -p "${FONT_DIR}"

# Download SF Pro if not present (Apple's free developer fonts)
if [[ ! -f "${FONT_DIR}/SF-Pro-Display-Regular.otf" ]]; then
    log "Note: SF Pro fonts must be downloaded from Apple Developer site."
    log "Placeholder: using Inter as fallback."
    # Install Inter as high-quality fallback
    apt-get install -y fonts-inter 2>/dev/null || {
        wget -qO /tmp/inter.zip "https://github.com/rsms/inter/releases/download/v4.0/Inter-4.0.zip"
        unzip -o /tmp/inter.zip -d /tmp/inter
        find /tmp/inter -name '*.ttf' -o -name '*.otf' | xargs -I{} cp {} "${FONT_DIR}/"
        rm -rf /tmp/inter /tmp/inter.zip
    }
fi

# Refresh font cache
fc-cache -f -v

# ── 6. GNOME Shell Extensions ──
log "Configuring Dash to Dock …"
apt-get install -y gnome-shell-extension-dash-to-dock 2>/dev/null || true

log "✅ macOS theme installation complete!"
log "Run 'macos-theme-switcher.sh' to apply, or reboot."
