#!/bin/bash
# ═══════════════════════════════════════════════════════════
# AegisNova OS — Live-Build Hook: Installer Integration
# ═══════════════════════════════════════════════════════════
# Ensures the installer script is available and executable
# in the live environment.
# ═══════════════════════════════════════════════════════════

set -e

echo "[AegisNova] Setting up disk installer..."

# Make installer executable
if [[ -f /usr/local/bin/aegisnova-install.sh ]]; then
    chmod +x /usr/local/bin/aegisnova-install.sh
    ln -sf /usr/local/bin/aegisnova-install.sh /usr/local/bin/aegisnova-install 2>/dev/null || true
fi

# Create desktop shortcut for installer
if [[ -d /etc/skel/Desktop ]]; then
    cat > /etc/skel/Desktop/aegisnova-install.desktop << 'EOF'
[Desktop Entry]
Name=Install AegisNova OS
Comment=Install AegisNova OS to your computer
Exec=sudo /usr/local/bin/aegisnova-install.sh
Type=Application
Icon=system-software-install
Terminal=true
Categories=System;
EOF
    chmod +x /etc/skel/Desktop/aegisnova-install.desktop
fi

# Create autostart for first-run welcome
mkdir -p /etc/skel/.config/autostart
cat > /etc/skel/.config/autostart/aegisnova-welcome.desktop << 'EOF'
[Desktop Entry]
Name=AegisNova Welcome
Comment=Welcome to AegisNova OS
Exec=/usr/local/bin/aegisnova-welcome.sh
Type=Application
Icon=aegisnova-logo
Terminal=false
Hidden=false
X-GNOME-Autostart-enabled=true
EOF

echo "[AegisNova] Installer integration complete."
