#!/usr/bin/env bash
# AegisNova OS — macOS Wallpaper Randomizer
# Selects a random wallpaper from the AegisNova collection and applies it.
set -euo pipefail

WALLPAPER_DIR="/usr/share/backgrounds/AegisNova"

if [[ ! -d "${WALLPAPER_DIR}" ]]; then
    echo "Wallpaper directory not found: ${WALLPAPER_DIR}"
    exit 1
fi

# Collect all image files
mapfile -t WALLPAPERS < <(find "${WALLPAPER_DIR}" -type f \( -name '*.jpg' -o -name '*.png' -o -name '*.webp' \) 2>/dev/null)

if [[ ${#WALLPAPERS[@]} -eq 0 ]]; then
    echo "No wallpapers found in ${WALLPAPER_DIR}"
    exit 1
fi

# Pick a random wallpaper
RANDOM_INDEX=$((RANDOM % ${#WALLPAPERS[@]}))
SELECTED="${WALLPAPERS[$RANDOM_INDEX]}"

echo "Setting wallpaper: ${SELECTED}"

# Apply to GNOME (both light and dark)
gsettings set org.gnome.desktop.background picture-uri "file://${SELECTED}"
gsettings set org.gnome.desktop.background picture-uri-dark "file://${SELECTED}"
gsettings set org.gnome.desktop.background picture-options "zoom"

echo "✅ Wallpaper applied."
