#!/bin/bash
# ═══════════════════════════════════════════════════════════
# AegisNova OS — Live-Build Hook: Boot Menu Customization
# ═══════════════════════════════════════════════════════════
# This hook customizes the GRUB and ISOLINUX boot menus
# for the AegisNova OS live ISO.
# ═══════════════════════════════════════════════════════════

set -e

# Colors for boot menu (dark military HUD blue accent)
AEGISNOVA_COLOR="#5a9fd4"
AEGISNOVA_BG="#0a0a0c"

echo "[AegisNova] Customizing boot menu..."

# ── Customize GRUB2 EFI Boot Menu ──
if [[ -d /boot/grub ]]; then
    cat > /boot/grub/aegisnova-theme.txt << 'EOF'
title-text: ""
title-color: #5a9fd4
message-color: #e0e0e5
message-bg-color: #0a0a0c
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

    # Minimal Plymouth script (dark blue spinner)
    cat > /usr/share/plymouth/themes/aegisnova/aegisnova.script << 'EOF'
# AegisNova Plymouth Script
screen_width = Window.GetWidth();
screen_height = Window.GetHeight();

# Dark background
bg = Image.Text("AEGIS NOVA", 1, 1, 1, 1, "Rajdhani", 32);
bg_sprite = Sprite(bg);
bg_sprite.SetX((screen_width - bg.GetWidth()) / 2);
bg_sprite.SetY(screen_height / 2 - 40);

# Blue spinner arc
spinner = Image.Arc(40, 40, 0, 3.14, 1, 1, 1, 0.35, 0.61, 0.83, 0.9);
spinner_sprite = Sprite(spinner);
spinner_sprite.SetX((screen_width - 80) / 2);
spinner_sprite.SetY(screen_height / 2 + 20);

fun refresh_callback () {
    spinner_sprite.SetImage(Image.Arc(40, 40, Math.PI * 2 * (GetTime() % 2) / 2, 3.14, 1, 1, 1, 0.35, 0.61, 0.83, 0.9));
}

Plymouth.SetRefreshFunction(refresh_callback);
EOF
fi

echo "[AegisNova] Boot menu customized."
