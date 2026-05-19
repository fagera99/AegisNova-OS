#!/bin/bash
set -e

BDIR="/opt/aegisnova_build/live-build-config"
ISO_OUT="/mnt/e/Linux_AI/AegisNova-OS.iso"

# Move binary dir if it's inside chroot
if [ -d "$BDIR/chroot/binary" ] && [ ! -d "$BDIR/binary" ]; then
  echo "[1/3] Moving binary directory..."
  cp -a "$BDIR/chroot/binary" "$BDIR/binary"
fi

echo "[2/3] Checking squashfs..."
ls -lh "$BDIR/binary/live/filesystem.squashfs" || {
  echo "ERROR: No squashfs found!"
  exit 1
}

# Check if isolinux exists, if not set up minimal boot
if [ ! -f "$BDIR/binary/isolinux/isolinux.bin" ]; then
  echo "[2.5/3] Setting up boot files..."
  mkdir -p "$BDIR/binary/isolinux"
  cp /usr/lib/ISOLINUX/isolinux.bin "$BDIR/binary/isolinux/" 2>/dev/null || true
  cp /usr/lib/syslinux/modules/bios/ldlinux.c32 "$BDIR/binary/isolinux/" 2>/dev/null || true
fi

echo "[3/3] Creating ISO on E: drive..."
cd "$BDIR"

# Try with available boot config
if [ -f "binary/isolinux/isolinux.bin" ]; then
  xorriso -as mkisofs \
    -o "$ISO_OUT" \
    -isohybrid-mbr /usr/lib/ISOLINUX/isohdpfx.bin \
    -c isolinux/boot.cat \
    -b isolinux/isolinux.bin \
    -no-emul-boot -boot-load-size 4 -boot-info-table \
    -V "AegisNova" \
    binary/
else
  # Fallback: simple ISO without boot
  xorriso -as mkisofs \
    -o "$ISO_OUT" \
    -V "AegisNova" \
    binary/
fi

echo "=== DONE ==="
ls -lh "$ISO_OUT"
echo "ISO file is at: E:\\Linux_AI\\AegisNova-OS.iso"
