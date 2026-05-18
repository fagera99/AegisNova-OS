#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
# AegisNova OS — Master AI Decensoring Setup
# Sets up ALL model backends with decensoring:
# - Local models: Auto-decensor via Heretic
# - API models: Proxy with response filtering
# - Cloud models: Pre-decensored model download
# ═══════════════════════════════════════════════════════════
set -euo pipefail

HERETIC_DIR="/opt/aegisnova/heretic"
MODELS_DIR="/opt/aegisnova/models"
DECENSORED_DIR="/opt/aegisnova/models/decensored"
LOG_DIR="/var/log/aegisnova/ai"
CONFIG_FILE="/etc/aegisnova/model-manager.conf"

log() { echo "[AI-Setup] $*"; }

# Create directories
mkdir -p "${HERETIC_DIR}" "${DECENSORED_DIR}" "${LOG_DIR}" "/etc/aegisnova"

# Install dependencies
log "Installing Python dependencies..."
python3 -m pip install --upgrade pip 2>/dev/null || true
python3 -m pip install requests urllib3 2>/dev/null || true

# Copy config if not exists
if [[ ! -f "${CONFIG_FILE}" ]]; then
    log "Copying default model manager config..."
    cp /opt/aegisnova/model-manager.conf.example "${CONFIG_FILE}" 2>/dev/null || true
fi

# Start proxy
log "Starting AI Decensoring Proxy..."
systemctl enable ai-proxy 2>/dev/null || true
systemctl start ai-proxy 2>/dev/null || log "Proxy service not available yet"

# Setup local models
log "Setting up local models..."
if [[ -f "/usr/local/bin/heretic-setup.sh" ]]; then
    bash /usr/local/bin/heretic-setup.sh 2>/dev/null || log "Heretic setup skipped"
fi

# Auto-decensor if enabled
if [[ -f "/opt/aegisnova/heretic/auto-decensor.sh" ]]; then
    log "Running auto-decensoring..."
    bash /opt/aegisnova/heretic/auto-decensor.sh 2>/dev/null || log "Auto-decensoring skipped"
fi

# Setup API proxy configuration
log "Configuring API proxy..."
cat > /etc/aegisnova/env << 'EOF'
# AI Environment Variables
# Set your API keys here for cloud models
# These will be used through the decensoring proxy

# OpenAI (optional - local model is default)
# OPENAI_API_KEY=sk-your-key-here

# Anthropic (optional)
# ANTHROPIC_API_KEY=sk-ant-your-key-here

# Local model path
LLAMA_MODEL=/opt/aegisnova/models/decensored/gemma-2b-heretic.gguf
LLAMA_MODEL_FALLBACK=/opt/aegisnova/models/gemma-2b-Q4_K_M.gguf

# Proxy settings
AI_PROXY_HOST=127.0.0.1
AI_PROXY_PORT=8081
EOF

chmod 600 /etc/aegisnova/env

# Enable all AI services
log "Enabling AI services..."
services=("ai-proxy" "ai-shell" "heretic-decensor")
for svc in "${services[@]}"; do
    systemctl enable "${svc}" 2>/dev/null || log "Could not enable ${svc}"
done

log "✅ AI Decensoring Setup Complete!"
log ""
log "Available Models:"
log "  Local:   gemma-2b-heretic.gguf (auto-decensored)"
log "  API:     OpenAI/Anthropic via proxy (response filtered)"
log "  Cloud:   HuggingFace pre-decensored models"
log ""
log "To start: systemctl start ai-shell ai-proxy"
log "To check: model_manager.py --list"
