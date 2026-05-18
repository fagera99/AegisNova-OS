#!/usr/bin/env bash
# ============================================================================
# AegisNova OS — Enhanced QEMU Smoke Test Suite
# ============================================================================
# Boots the ISO in QEMU, waits for the system to start, and runs a
# comprehensive battery of checks to verify core functionality and security.
#
# Usage: ./smoke-test.sh <path-to-iso>
# ============================================================================
set -euo pipefail

ISO_FILE="${1:?Usage: smoke-test.sh <iso-file>}"
RESULTS_DIR="$(dirname "$0")/results"
QEMU_PORT=2222
TIMEOUT=240
QEMU_PID=""

mkdir -p "${RESULTS_DIR}"

log()  { echo -e "\e[1;34m[SMOKE]\e[0m $*" | tee -a "${RESULTS_DIR}/smoke.log"; }
pass() { echo -e "\e[1;32m[PASS]\e[0m $*" | tee -a "${RESULTS_DIR}/smoke.log"; }
fail() { echo -e "\e[1;31m[FAIL]\e[0m $*" | tee -a "${RESULTS_DIR}/smoke.log"; }

cleanup() {
    if [[ -n "${QEMU_PID}" ]]; then
        kill "${QEMU_PID}" 2>/dev/null || true
    fi
}
trap cleanup EXIT

# ── Start QEMU ──
log "Booting ISO: ${ISO_FILE}"
qemu-system-x86_64 \
    -m 4096 \
    -smp 2 \
    -cdrom "${ISO_FILE}" \
    -boot d \
    -nographic \
    -serial mon:stdio \
    -net nic -net user,hostfwd=tcp::${QEMU_PORT}-:22 \
    -no-reboot &
QEMU_PID=$!

# ── Wait for SSH ──
log "Waiting for system to boot (max ${TIMEOUT}s) ..."
ELAPSED=0
while ! ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 \
    -p ${QEMU_PORT} root@localhost "echo ready" 2>/dev/null; do
    sleep 10
    ELAPSED=$((ELAPSED + 10))
    if [[ ${ELAPSED} -ge ${TIMEOUT} ]]; then
        fail "System did not boot within ${TIMEOUT}s"
        exit 1
    fi
    log "  Waiting ... (${ELAPSED}s)"
done
pass "System booted successfully."

# ── Helper: run command in VM ──
vm_run() {
    ssh -o StrictHostKeyChecking=no -p ${QEMU_PORT} root@localhost "$@"
}

# ── Test 1: AI services are running ──
log "Test 1: Checking AI services ..."
SERVICES=(ai-shell ebpf-sensor)
for svc in "${SERVICES[@]}"; do
    if vm_run "systemctl is-active ${svc}" 2>/dev/null | grep -q "active"; then
        pass "  ${svc}.service is active"
    else
        fail "  ${svc}.service is NOT active"
    fi
done

# ── Test 2: Docker is running ──
log "Test 2: Checking Docker ..."
if vm_run "docker info" &>/dev/null; then
    pass "  Docker is running"
else
    fail "  Docker is NOT running"
fi

# ── Test 3: nmap loopback scan ──
log "Test 3: nmap loopback scan ..."
NMAP_OUT=$(vm_run "nmap -sT -T4 127.0.0.1 --top-ports 20" 2>/dev/null)
if echo "${NMAP_OUT}" | grep -q "open"; then
    pass "  nmap scan completed — open ports detected"
    echo "${NMAP_OUT}" > "${RESULTS_DIR}/nmap-loopback.txt"
else
    fail "  nmap scan found no open ports"
fi

# ── Test 4: eBPF sensor detection ──
log "Test 4: eBPF sensor log check ..."
SENSOR_LOG=$(vm_run "journalctl -u ebpf-sensor --no-pager -n 20" 2>/dev/null)
if echo "${SENSOR_LOG}" | grep -qi "started\|probe\|event"; then
    pass "  eBPF sensor is logging events"
    echo "${SENSOR_LOG}" > "${RESULTS_DIR}/ebpf-sensor.log"
else
    fail "  eBPF sensor has no log entries"
fi

# ── Test 5: Kernel version ──
log "Test 5: Kernel version check ..."
KVER=$(vm_run "uname -r" 2>/dev/null)
if echo "${KVER}" | grep -q "aegisnova"; then
    pass "  Custom kernel detected: ${KVER}"
else
    fail "  Expected custom kernel, got: ${KVER}"
fi

# ── Test 6: Security hardening ──
log "Test 6: Sysctl hardening ..."
KPTR=$(vm_run "cat /proc/sys/kernel/kptr_restrict" 2>/dev/null)
if [[ "${KPTR}" == "2" ]]; then
    pass "  kptr_restrict = 2"
else
    fail "  kptr_restrict = ${KPTR} (expected 2)"
fi

# ── Test 7: AI Model Manager ──
log "Test 7: AI Model Manager availability ..."
if vm_run "python3 /usr/local/bin/model_manager.py --list" 2>/dev/null | grep -q "Available"; then
    pass "  Model manager is accessible"
else
    fail "  Model manager not accessible"
fi

# ── Test 8: MITRE ATT&CK Agent ──
log "Test 8: MITRE ATT&CK agent ..."
if vm_run "python3 /usr/local/bin/mitre-attack-agent.py --lookup T1003" 2>/dev/null | grep -q "OS Credential Dumping"; then
    pass "  MITRE ATT&CK agent working"
else
    fail "  MITRE ATT&CK agent failed"
fi

# ── Test 9: Sigma Rule Generator ──
log "Test 9: Sigma rule generator ..."
if vm_run "python3 /usr/local/bin/sigma-generator.py --technique T1558.003 --output /tmp/test-sigma.yml" 2>/dev/null; then
    pass "  Sigma rule generator working"
else
    fail "  Sigma rule generator failed"
fi

# ── Test 10: OSINT Agent ──
log "Test 10: OSINT agent ..."
if vm_run "python3 /usr/local/bin/osint-agent.py --ip 127.0.0.1 --output /tmp/osint-test.json" 2>/dev/null | grep -q "OSINT"; then
    pass "  OSINT agent working"
else
    fail "  OSINT agent failed"
fi

# ── Test 11: IR Playbook ──
log "Test 11: Incident Response playbook ..."
if vm_run "python3 /usr/local/bin/ir-playbook.py --list" 2>/dev/null | grep -q "Malware Detection"; then
    pass "  IR playbook accessible"
else
    fail "  IR playbook not accessible"
fi

# ── Test 12: Security tools availability ──
log "Test 12: Security tools availability ..."
TOOLS=(nmap metasploit-framework suricata wazuh-agent lynis yara volatility3)
for tool in "${TOOLS[@]}"; do
    if vm_run "dpkg -l ${tool}" &>/dev/null || vm_run "which ${tool}" &>/dev/null; then
        pass "  ${tool} is installed"
    else
        fail "  ${tool} is NOT installed"
    fi
done

# ── Test 13: Firewall configuration ──
log "Test 13: Firewall configuration ..."
if vm_run "nft list ruleset" 2>/dev/null | grep -q "chain"; then
    pass "  nftables firewall is configured"
else
    fail "  nftables firewall not configured"
fi

# ── Test 14: Audit daemon ──
log "Test 14: Audit daemon ..."
if vm_run "systemctl is-active auditd" 2>/dev/null | grep -q "active"; then
    pass "  auditd is running"
else
    fail "  auditd is NOT running"
fi

# ── Test 15: macOS theme ──
log "Test 15: macOS theme files ..."
if vm_run "ls /opt/aegisnova/theme/" 2>/dev/null | grep -q "install"; then
    pass "  macOS theme assets present"
else
    fail "  macOS theme assets missing"
fi

# ── Test 16: AegisNova scripts ──
log "Test 16: AegisNova utility scripts ..."
SCRIPTS=(aegisnova-update aegisnova-vulnscan aegisnova-persistence-setup aegisnova-mok-enroll)
for script in "${SCRIPTS[@]}"; do
    if vm_run "test -x /usr/local/bin/${script}.sh" 2>/dev/null; then
        pass "  ${script}.sh is present and executable"
    else
        fail "  ${script}.sh is missing or not executable"
    fi
done

# ── Test 17: Docker compose files ──
log "Test 17: Docker compose stacks ..."
if vm_run "ls /opt/aegisnova/docker/" 2>/dev/null | grep -q "yml"; then
    pass "  Docker compose stacks present"
else
    fail "  Docker compose stacks missing"
fi

# ── Test 18: Log directories ──
log "Test 18: AegisNova log directories ..."
if vm_run "ls /var/log/aegisnova/" 2>/dev/null | grep -q "ai"; then
    pass "  Log directories created"
else
    fail "  Log directories missing"
fi

# ── Test 19: SELinux/AppArmor ──
log "Test 19: Mandatory Access Control ..."
if vm_run "command -v getenforce" &>/dev/null || vm_run "command -v aa-status" &>/dev/null; then
    pass "  MAC frameworks installed"
else
    fail "  MAC frameworks not installed"
fi

# ── Test 20: File integrity ──
log "Test 20: File integrity tools ..."
if vm_run "command -v aide" &>/dev/null || vm_run "command -v tripwire" &>/dev/null; then
    pass "  File integrity tools installed"
else
    fail "  File integrity tools missing"
fi

# ── Summary ──
log ""
log "═══════════════════════════════════════════════════════"
log "  Enhanced smoke test suite complete."
log "  Results saved to: ${RESULTS_DIR}/"
log "═══════════════════════════════════════════════════════"

# Count pass/fail
PASSED=$(grep -c "\[PASS\]" "${RESULTS_DIR}/smoke.log" || true)
FAILED=$(grep -c "\[FAIL\]" "${RESULTS_DIR}/smoke.log" || true)
log "  Passed: ${PASSED}  |  Failed: ${FAILED}"

[[ "${FAILED}" -eq 0 ]] && exit 0 || exit 1
