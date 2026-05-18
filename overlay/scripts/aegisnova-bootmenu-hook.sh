#!/bin/bash
# ═══════════════════════════════════════════════════════════
# AegisNova OS — Live-Build Hook: Boot Menu Customization
# ═══════════════════════════════════════════════════════════
# This hook customizes the GRUB and ISOLINUX boot menus
# for the AegisNova OS live ISO.
# ═══════════════════════════════════════════════════════════

set -e

# Colors for boot menu
AEGISNOVA_COLOR="#00FF88"
AEGISNOVA_BG="#1A1A1A"

echo "[AegisNova] Customizing boot menu..."

# ── Customize GRUB2 EFI Boot Menu ──
if [[ -d /boot/grub ]]; then
    cat > /boot/grub/aegisnova-theme.txt << 'EOF'
title-text: ""
desktop-image: "background.jpg"
title-color: #00FF88
message-color: #CCCCCC
message-bg-color: #1A1A1A
terminal-box: "terminal_box_*.png"
EOF

    # Update GRUB config for AegisNova
    if [[ -f /etc/grub.d/00_header ]]; then
        sed -i 's/timeout=.*/timeout=10/' /etc/default/grub 2>/dev/null || true
        sed -i 's/GRUB_TIMEOUT=.*/GRUB_TIMEOUT=10/' /etc/default/grub 2>/dev/null || true
    fi
fi

# ── Create custom GRUB entries ──
if [[ -d /etc/grub.d ]]; then
    cat > /etc/grub.d/99_aegisnova << 'GRUBEOF'
#!/bin/sh
exec tail -n +3 $0

# AegisNova OS Custom Entries
menuentry "AegisNova OS — Live (amd64)" --class aegisnova {
    linux /live/vmlinuz boot=live components quiet splash
    initrd /live/initrd.img
}

menuentry "AegisNova OS — Live with Persistence" --class aegisnova {
    linux /live/vmlinuz boot=live components quiet splash persistence persistence-encryption=luks
    initrd /live/initrd.img
}

menuentry "AegisNova OS — Live (Forensic Mode)" --class aegisnova {
    linux /live/vmlinuz boot=live components quiet splash noswap noautomount
    initrd /live/initrd.img
}

menuentry "AegisNova OS — Install to Disk" --class aegisnova {
    linux /live/vmlinuz boot=live components quiet splash aegisnova-install
    initrd /live/initrd.img
}

menuentry "AegisNova OS — RAM Test (memtest86+)" --class memtest {
    linux16 /live/memtest86+.bin
}

menuentry "AegisNova OS — Boot from Hard Drive" --class os {
    set root=(hd0,1)
    chainloader +1
}
GRUBEOF

    chmod +x /etc/grub.d/99_aegisnova
fi

# ── Create Plymouth theme reference ──
if [[ -d /usr/share/plymouth ]]; then
    mkdir -p /usr/share/plymouth/themes/aegisnova
    cat > /usr/share/plymouth/themes/aegisnova/aegisnova.plymouth << 'EOF'
[Plymouth Theme]
Name=AegisNova OS
Description=AegisNova OS Boot Theme
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/aegisnova
ScriptFile=/usr/share/plymouth/themes/aegisnova/aegisnova.script
EOF
fi

echo "[AegisNova] Boot menu customized."
