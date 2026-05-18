#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════
# AegisNova OS — Heretic Setup Script
# Installs heretic-llm and prepares decensoring pipeline
# ═══════════════════════════════════════════════════════════
set -euo pipefail

HERETIC_DIR="/opt/aegisnova/heretic"
MODELS_DIR="/opt/aegisnova/models"
DECENSORED_DIR="/opt/aegisnova/models/decensored"
VENV_DIR="${HERETIC_DIR}/venv"

log() { echo "[heretic-setup] $*"; }

# Create directories
mkdir -p "${HERETIC_DIR}" "${DECENSORED_DIR}"

# Create Python virtual environment
if [[ ! -d "${VENV_DIR}" ]]; then
    log "Creating Python virtual environment …"
    python3 -m venv "${VENV_DIR}"
fi

# Install heretic
log "Installing heretic-llm …"
"${VENV_DIR}/bin/pip" install --upgrade pip
"${VENV_DIR}/bin/pip" install -U heretic-llm

# Create decensor wrapper script
cat > "${HERETIC_DIR}/decensor-model.sh" << 'EOF'
#!/usr/bin/env bash
# Decensor a model using Heretic
set -euo pipefail

MODEL_INPUT="${1:-}"
MODEL_OUTPUT="${2:-}"

if [[ -z "${MODEL_INPUT}" || -z "${MODEL_OUTPUT}" ]]; then
    echo "Usage: decensor-model.sh <input-model> <output-model>"
    echo "Example: decensor-model.sh gemma-2b-Q4_K_M.gguf gemma-2b-decensored.gguf"
    exit 1
fi

VENV_DIR="/opt/aegisnova/heretic/venv"
DECENSORED_DIR="/opt/aegisnova/models/decensored"
mkdir -p "${DECENSORED_DIR}"

# Convert GGUF to HF format if needed
INPUT_PATH="/opt/aegisnova/models/${MODEL_INPUT}"
OUTPUT_NAME="${MODEL_OUTPUT%.gguf}"

echo "[heretic] Decensoring ${MODEL_INPUT} …"
echo "[heretic] This may take 30-90 minutes depending on model size and GPU …"

cd "${DECENSORED_DIR}"

# Run heretic on the model
"${VENV_DIR}/bin/heretic" \
    --model "${INPUT_PATH}" \
    --output "${OUTPUT_NAME}" \
    --quantization bnb_4bit \
    --save

echo "[heretic] Decensored model saved to: ${DECENSORED_DIR}/${OUTPUT_NAME}"
EOF

chmod +x "${HERETIC_DIR}/decensor-model.sh"

# Create auto-decensor script for default model
cat > "${HERETIC_DIR}/auto-decensor.sh" << 'EOF'
#!/usr/bin/env bash
# Auto-decensor the default Gemma model if not already decensored
set -euo pipefail

MODELS_DIR="/opt/aegisnova/models"
DECENSORED_DIR="/opt/aegisnova/models/decensored"

# Check if decensored model exists
if [[ -f "${DECENSORED_DIR}/gemma-2b-heretic.gguf" ]]; then
    echo "[heretic] Decensored model already exists."
    exit 0
fi

# Check if base model exists
if [[ ! -f "${MODELS_DIR}/gemma-2b-Q4_K_M.gguf" ]]; then
    echo "[heretic] Base model not found. Skipping auto-decensor."
    exit 0
fi

echo "[heretic] Auto-decensoring default model …"
/opt/aegisnova/heretic/decensor-model.sh \
    gemma-2b-Q4_K_M.gguf \
    gemma-2b-heretic.gguf
EOF

chmod +x "${HERETIC_DIR}/auto-decensor.sh"

log "Heretic setup complete."
log "Usage:"
log "  /opt/aegisnova/heretic/decensor-model.sh <input> <output>"
log "  /opt/aegisnova/heretic/auto-decensor.sh"
