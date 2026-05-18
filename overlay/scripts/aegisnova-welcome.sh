#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
# AegisNova OS — Welcome Script (First Boot)
# ═══════════════════════════════════════════════════════════
# Runs on first login to welcome the user and offer setup.
# ═══════════════════════════════════════════════════════════

TERMINAL="gnome-terminal"

# Check if we're in a graphical environment
if [[ -z "${DISPLAY}" ]]; then
    exit 0
fi

# Show welcome dialog (using zenity if available, otherwise simple echo)
if command -v zenity &>/dev/null; then
    zenity --info \
        --title="Welcome to AegisNova OS" \
        --text="<big><b>Welcome to AegisNova OS!</b></big>\n\nYour AI-Augmented Security Distribution is ready.\n\nQuick Actions:\n• Install to Disk: sudo aegisnova-install\n• Start AI Shell: ai-shell \"your question\"\n• Apply Hardening: sudo harden-system.sh\n\nOpen a terminal for the full experience." \
        --width=400 \
        --icon-name=security-high 2>/dev/null || true
else
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    echo "  Welcome to AegisNova OS!"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    echo "  Your AI-Augmented Security Distribution is ready."
    echo ""
    echo "  Quick Actions:"
    echo "    • Install to Disk:    sudo aegisnova-install"
    echo "    • Start AI Shell:     ai-shell \"your question\""
    echo "    • Apply Hardening:    sudo harden-system.sh"
    echo "    • Vulnerability Scan: sudo aegisnova-vulnscan --now"
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
fi
