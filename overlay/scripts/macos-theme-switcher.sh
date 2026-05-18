#!/usr/bin/env bash
# ============================================================================
# AegisNova OS — macOS Theme Switcher
# ============================================================================
# Reads /etc/aegisnova/macos-theme.conf and applies the corresponding
# GTK/GNOME Shell theme, icons, cursor, and color scheme.
#
# Config values: THEME_MODE=light|dark
# ============================================================================
set -euo pipefail

CONFIG_FILE="/etc/aegisnova/macos-theme.conf"

# Defaults
THEME_MODE="dark"
GTK_THEME_LIGHT="WhiteSur-Light"
GTK_THEME_DARK="WhiteSur-Dark"
SHELL_THEME_LIGHT="WhiteSur-Light"
SHELL_THEME_DARK="WhiteSur-Dark"
ICON_THEME="McMojave-circle"
CURSOR_THEME="macOS-cursor"
FONT_NAME="SF Pro Display 11"
MONOSPACE_FONT="Menlo 12"

# Read config
if [[ -f "${CONFIG_FILE}" ]]; then
    # shellcheck source=/dev/null
    source "${CONFIG_FILE}"
fi

log() { echo "[macos-theme] $*"; }

# Wait for GNOME session
sleep 2

apply_theme() {
    local gtk_theme shell_theme color_scheme

    if [[ "${THEME_MODE}" == "light" ]]; then
        gtk_theme="${GTK_THEME_LIGHT}"
        shell_theme="${SHELL_THEME_LIGHT}"
        color_scheme="prefer-light"
    else
        gtk_theme="${GTK_THEME_DARK}"
        shell_theme="${SHELL_THEME_DARK}"
        color_scheme="prefer-dark"
    fi

    log "Applying ${THEME_MODE} theme …"

    # GTK theme
    gsettings set org.gnome.desktop.interface gtk-theme "${gtk_theme}" 2>/dev/null || true
    gsettings set org.gnome.desktop.interface color-scheme "${color_scheme}" 2>/dev/null || true

    # GNOME Shell theme
    gsettings set org.gnome.shell.extensions.user-theme name "${shell_theme}" 2>/dev/null || true

    # Icons
    gsettings set org.gnome.desktop.interface icon-theme "${ICON_THEME}" 2>/dev/null || true

    # Cursor
    gsettings set org.gnome.desktop.interface cursor-theme "${CURSOR_THEME}" 2>/dev/null || true
    gsettings set org.gnome.desktop.interface cursor-size 24 2>/dev/null || true

    # Fonts
    gsettings set org.gnome.desktop.interface font-name "${FONT_NAME}" 2>/dev/null || true
    gsettings set org.gnome.desktop.interface monospace-font-name "${MONOSPACE_FONT}" 2>/dev/null || true
    gsettings set org.gnome.desktop.interface document-font-name "SF Pro Display 11" 2>/dev/null || true
    gsettings set org.gnome.desktop.wm.preferences titlebar-font "SF Pro Display Bold 11" 2>/dev/null || true

    # Window buttons (macOS layout: close/minimize/maximize on left)
    gsettings set org.gnome.desktop.wm.preferences button-layout "close,minimize,maximize:" 2>/dev/null || true

    # Dash to Dock — macOS preset
    local DOCK_SCHEMA="org.gnome.shell.extensions.dash-to-dock"
    gsettings set "${DOCK_SCHEMA}" dock-position 'BOTTOM' 2>/dev/null || true
    gsettings set "${DOCK_SCHEMA}" dock-fixed true 2>/dev/null || true
    gsettings set "${DOCK_SCHEMA}" extend-height false 2>/dev/null || true
    gsettings set "${DOCK_SCHEMA}" dash-max-icon-size 48 2>/dev/null || true
    gsettings set "${DOCK_SCHEMA}" transparency-mode 'DYNAMIC' 2>/dev/null || true
    gsettings set "${DOCK_SCHEMA}" background-opacity 0.6 2>/dev/null || true
    gsettings set "${DOCK_SCHEMA}" custom-theme-shrink true 2>/dev/null || true
    gsettings set "${DOCK_SCHEMA}" running-indicator-style 'DOTS' 2>/dev/null || true
    gsettings set "${DOCK_SCHEMA}" show-trash false 2>/dev/null || true
    gsettings set "${DOCK_SCHEMA}" show-mounts false 2>/dev/null || true
    gsettings set "${DOCK_SCHEMA}" click-action 'minimize-or-previews' 2>/dev/null || true

    # Set wallpaper
    /usr/local/bin/set-macos-wallpaper.sh 2>/dev/null || true

    log "✅ ${THEME_MODE} macOS theme applied."
}

apply_theme
