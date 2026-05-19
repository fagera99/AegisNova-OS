#!/bin/bash
echo "=== Testing Shell Scripts ==="
for f in /mnt/e/Linux_AI/overlay/scripts/*.sh; do
    name=$(basename "$f")
    if bash -n "$f" 2>/tmp/sherr; then
        echo "OK: $name"
    else
        echo "BUG: $name -> $(cat /tmp/sherr)"
    fi
done

echo ""
echo "=== Testing Python Scripts ==="
for f in /mnt/e/Linux_AI/overlay/scripts/*.py; do
    name=$(basename "$f")
    if python3 -m py_compile "$f" 2>/tmp/pyerr; then
        echo "OK: $name"
    else
        echo "BUG: $name -> $(cat /tmp/pyerr)"
    fi
done

echo ""
echo "=== Testing Jarvis Auto-Start ==="
# Check service file exists
if [ -f /mnt/e/Linux_AI/overlay/systemd/aegis-assistant.service ]; then
    echo "OK: aegis-assistant.service exists"
else
    echo "BUG: aegis-assistant.service MISSING"
fi

# Check the shebang line of aegisnova-assistant.py
head -1 /mnt/e/Linux_AI/overlay/scripts/aegisnova-assistant.py
echo ""
echo "=== DONE ==="
