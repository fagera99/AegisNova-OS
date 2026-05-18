#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
# AegisNova OS — Automated Vulnerability Scanning Scheduler
# ═══════════════════════════════════════════════════════════
# Schedules and runs automated vulnerability scans using:
# - OpenVAS/GVM
# - Lynis (system audit)
# - Trivy (container scanning)
# - Nuclei (web vulnerability scanning)
# - Custom network scans
#
# Usage: sudo aegisnova-vulnscan [--now] [--schedule] [--report]
# ═══════════════════════════════════════════════════════════
set -euo pipefail

SCAN_DIR="/var/log/aegisnova/scans"
REPORT_DIR="/var/log/aegisnova/reports"
CONFIG_FILE="/etc/aegisnova/vulnscan.conf"
RUN_NOW=false
SETUP_SCHEDULE=false
GENERATE_REPORT=false

log()  { echo -e "\e[1;32m[VULNSCAN]\e[0m $*"; }
err()  { echo -e "\e[1;31m[ERROR]\e[0m $*" >&2; exit 1; }
warn() { echo -e "\e[1;33m[WARN]\e[0m $*"; }

# ── Parse args ──
while [[ $# -gt 0 ]]; do
    case "$1" in
        --now)      RUN_NOW=true; shift ;;
        --schedule) SETUP_SCHEDULE=true; shift ;;
        --report)   GENERATE_REPORT=true; shift ;;
        *)          err "Unknown option: $1"; ;;
    esac
done

# ── Check root ──
[[ $EUID -eq 0 ]] || err "Must be run as root."

# ── Create directories ──
mkdir -p "${SCAN_DIR}" "${REPORT_DIR}"

# ── Default config ──
if [[ ! -f "${CONFIG_FILE}" ]]; then
    cat > "${CONFIG_FILE}" << 'EOF'
# AegisNova Vulnerability Scan Configuration

# Network targets (space-separated)
TARGETS="127.0.0.1"

# Scan schedules (cron format)
DAILY_SCAN="0 2 * * *"
WEEKLY_SCAN="0 3 * * 0"
MONTHLY_SCAN="0 4 1 * *"

# Scan types to enable
ENABLE_OPENVAS=true
ENABLE_LYNIS=true
ENABLE_TRIVY=true
ENABLE_NUCLEI=true
ENABLE_NETWORK=true

# Reporting
EMAIL_REPORTS=false
EMAIL_ADDRESS=""
SLACK_WEBHOOK=""
EOF
    chmod 600 "${CONFIG_FILE}"
    log "Created default config: ${CONFIG_FILE}"
fi

# Source config
# shellcheck source=/dev/null
source "${CONFIG_FILE}"

# ═══════════════════════════════════════════════════════════
# Scan Functions
# ═══════════════════════════════════════════════════════════

run_lynis_scan() {
    log "Running Lynis system audit..."
    local report_file="${SCAN_DIR}/lynis-$(date +%Y%m%d-%H%M%S).log"
    
    lynis audit system --quick --no-colors --report-file "${report_file}" 2>/dev/null || true
    
    if [[ -f "${report_file}" ]]; then
        log "Lynis report saved: ${report_file}"
        
        # Extract warnings and suggestions
        local warnings=$(grep -c "Warning:" "${report_file}" 2>/dev/null || echo "0")
        local suggestions=$(grep -c "Suggestion:" "${report_file}" 2>/dev/null || echo "0")
        log "  Warnings: ${warnings}, Suggestions: ${suggestions}"
    fi
}

run_trivy_scan() {
    log "Running Trivy container/image scan..."
    local report_file="${SCAN_DIR}/trivy-$(date +%Y%m%d-%H%M%S).json"
    
    # Scan running containers
    if command -v docker &>/dev/null; then
        local containers=$(docker ps -q 2>/dev/null || true)
        if [[ -n "${containers}" ]]; then
            for container in ${containers}; do
                local image=$(docker inspect --format='{{.Config.Image}}' "${container}" 2>/dev/null || true)
                if [[ -n "${image}" ]]; then
                    log "  Scanning image: ${image}"
                    trivy image --format json --output "${report_file}.${container}" "${image}" 2>/dev/null || true
                fi
            done
        else
            log "  No running containers found."
        fi
    fi
    
    # Scan filesystem
    trivy filesystem --format json --output "${report_file}.fs" / 2>/dev/null || true
}

run_nuclei_scan() {
    log "Running Nuclei web vulnerability scan..."
    local report_file="${SCAN_DIR}/nuclei-$(date +%Y%m%d-%H%M%S).json"
    
    if command -v nuclei &>/dev/null; then
        for target in ${TARGETS}; do
            log "  Scanning target: ${target}"
            nuclei -u "${target}" -j -o "${report_file}.${target}" 2>/dev/null || true
        done
    else
        warn "Nuclei not installed. Skipping web scan."
    fi
}

run_network_scan() {
    log "Running network vulnerability scan..."
    local report_file="${SCAN_DIR}/network-$(date +%Y%m%d-%H%M%S).xml"
    
    for target in ${TARGETS}; do
        log "  Scanning: ${target}"
        nmap -sV -sC -T4 -p- --top-ports 1000 --script vuln "${target}" -oX "${report_file}.${target}" 2>/dev/null || true
    done
}

run_openvas_scan() {
    log "Running OpenVAS vulnerability scan..."
    local report_file="${SCAN_DIR}/openvas-$(date +%Y%m%d-%H%M%S).xml"
    
    if command -v gvm-cli &>/dev/null; then
        # Check if GVM is running
        if systemctl is-active --quiet gvmd 2>/dev/null; then
            log "  OpenVAS/GVM is running. Creating and starting scan..."
            # This would require more complex GVM XML commands
            # For now, just log that it should be configured
            log "  NOTE: Configure OpenVAS scans via Greenbone Security Assistant"
        else
            warn "  OpenVAS/GVM service not running. Start with:"
            warn "    systemctl start gvmd"
        fi
    else
        warn "OpenVAS/GVM not installed. Skipping."
    fi
}

# ═══════════════════════════════════════════════════════════
# Report Generation
# ═══════════════════════════════════════════════════════════

generate_combined_report() {
    log "Generating combined vulnerability report..."
    local report_file="${REPORT_DIR}/vulnscan-report-$(date +%Y%m%d).html"
    
    cat > "${report_file}" << EOF
<!DOCTYPE html>
<html>
<head>
    <title>AegisNova Vulnerability Scan Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #1a1a1a; color: #e0e0e0; }
        h1, h2 { color: #00ff88; }
        .critical { color: #ff4444; }
        .high { color: #ff8844; }
        .medium { color: #ffcc44; }
        .low { color: #44ff44; }
        .info { color: #4488ff; }
        table { border-collapse: collapse; width: 100%; margin: 20px 0; }
        th, td { border: 1px solid #333; padding: 8px; text-align: left; }
        th { background-color: #2a2a2a; }
        tr:nth-child(even) { background-color: #222; }
        .summary { background: #2a2a2a; padding: 15px; border-radius: 5px; margin: 20px 0; }
    </style>
</head>
<body>
    <h1>AegisNova Vulnerability Scan Report</h1>
    <div class="summary">
        <h2>Scan Summary</h2>
        <p><strong>Date:</strong> $(date -Iseconds)</p>
        <p><strong>Targets:</strong> ${TARGETS}</p>
        <p><strong>System:</strong> $(uname -a)</p>
    </div>
    
    <h2>Scan Results</h2>
    <table>
        <tr>
            <th>Scan Type</th>
            <th>Status</th>
            <th>Report File</th>
        </tr>
EOF
    
    # Add scan results
    for scan_file in "${SCAN_DIR}"/*-$(date +%Y%m%d)*.*; do
        if [[ -f "${scan_file}" ]]; then
            local scan_name=$(basename "${scan_file}" | cut -d'-' -f1)
            local scan_status="Completed"
            local file_size=$(du -h "${scan_file}" | cut -f1)
            
            cat >> "${report_file}" << EOF
        <tr>
            <td>${scan_name}</td>
            <td>${scan_status}</td>
            <td>${scan_file} (${file_size})</td>
        </tr>
EOF
        fi
    done
    
    cat >> "${report_file}" << EOF
    </table>
    
    <h2>Recommendations</h2>
    <ul>
        <li>Review all HIGH and CRITICAL findings immediately</li>
        <li>Apply security patches for identified vulnerabilities</li>
        <li>Update firewall rules based on network scan results</li>
        <li>Run Lynis suggestions to improve system hardening</li>
    </ul>
    
    <p><em>Generated by AegisNova Vulnerability Scanner</em></p>
</body>
</html>
EOF
    
    log "Report generated: ${report_file}"
}

# ═══════════════════════════════════════════════════════════
# Schedule Setup
# ═══════════════════════════════════════════════════════════

setup_cron_schedule() {
    log "Setting up scan schedules..."
    
    # Create cron jobs
    local cron_file="/etc/cron.d/aegisnova-vulnscan"
    
    cat > "${cron_file}" << EOF
# AegisNova Automated Vulnerability Scanning
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

# Daily quick scan
${DAILY_SCAN} root /usr/local/bin/aegisnova-vulnscan --now >/dev/null 2>&1

# Weekly full report
${WEEKLY_SCAN} root /usr/local/bin/aegisnova-vulnscan --now --report >/dev/null 2>&1
EOF
    
    chmod 644 "${cron_file}"
    log "Cron schedule installed: ${cron_file}"
    log "  Daily scan: ${DAILY_SCAN}"
    log "  Weekly scan + report: ${WEEKLY_SCAN}"
}

# ═══════════════════════════════════════════════════════════
# Main Execution
# ═══════════════════════════════════════════════════════════

if ${RUN_NOW}; then
    log "═══════════════════════════════════════════════════════════════"
    log "  Starting Vulnerability Scans"
    log "  Targets: ${TARGETS}"
    log "═══════════════════════════════════════════════════════════════"
    
    [[ "${ENABLE_LYNIS:-true}" == "true" ]] && run_lynis_scan
    [[ "${ENABLE_TRIVY:-true}" == "true" ]] && run_trivy_scan
    [[ "${ENABLE_NUCLEI:-true}" == "true" ]] && run_nuclei_scan
    [[ "${ENABLE_NETWORK:-true}" == "true" ]] && run_network_scan
    [[ "${ENABLE_OPENVAS:-true}" == "true" ]] && run_openvas_scan
    
    if ${GENERATE_REPORT}; then
        generate_combined_report
    fi
    
    log "═══════════════════════════════════════════════════════════════"
    log "  ✅ Scans Complete"
    log "  Reports: ${SCAN_DIR}/"
    log "═══════════════════════════════════════════════════════════════"
fi

if ${SETUP_SCHEDULE}; then
    setup_cron_schedule
    log "✅ Scan scheduling configured."
fi

if ! ${RUN_NOW} && ! ${SETUP_SCHEDULE}; then
    log "AegisNova Vulnerability Scanning Scheduler"
    log ""
    log "Usage:"
    log "  aegisnova-vulnscan --now        Run scans immediately"
    log "  aegisnova-vulnscan --now --report  Run scans and generate report"
    log "  aegisnova-vulnscan --schedule   Setup automatic scheduling"
    log ""
    log "Configuration: ${CONFIG_FILE}"
    log "Scan results: ${SCAN_DIR}/"
    log "Reports: ${REPORT_DIR}/"
fi
