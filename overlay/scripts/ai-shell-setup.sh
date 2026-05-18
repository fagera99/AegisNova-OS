#!/usr/bin/env bash
# AegisNova OS — AI Shell Setup Script
# Called by ai-shell.service ExecStartPre to bootstrap the LLM server.
set -euo pipefail

MODELS_DIR="/opt/aegisnova/models"
LLAMA_DIR="/opt/aegisnova/llama.cpp"
MODEL_URL="https://huggingface.co/google/gemma-2b-GGUF/resolve/main/gemma-2b-Q4_K_M.gguf"
MODEL_FILE="${MODELS_DIR}/gemma-2b-Q4_K_M.gguf"
DECENSORED_MODEL="${MODELS_DIR}/decensored/gemma-2b-heretic.gguf"

log() { echo "[ai-shell-setup] $*"; }

# Ensure directories exist
mkdir -p "${MODELS_DIR}"

# Download model if not present
if [[ ! -f "${MODEL_FILE}" ]]; then
    log "Downloading Gemma-2B model (Q4_K_M quantization) …"
    wget -q --show-progress -O "${MODEL_FILE}" "${MODEL_URL}" || {
        log "WARNING: Model download failed. Set LLAMA_MODEL env to a local .gguf file."
    }
fi

# Check for decensored model
if [[ -f "${DECENSORED_MODEL}" ]]; then
    log "Decensored model found: ${DECENSORED_MODEL}"
    log "AI agents will use uncensored model."
else
    log "No decensored model found. Run: systemctl start heretic-decensor"
    log "Falling back to base model."
fi

# Build llama.cpp if not present
if [[ ! -x "${LLAMA_DIR}/server" ]]; then
    log "Building llama.cpp from source …"
    mkdir -p "${LLAMA_DIR}"
    cd /tmp
    git clone --depth 1 https://github.com/ggerganov/llama.cpp.git llama-build
    cd llama-build
    make -j"$(nproc)" server
    cp server "${LLAMA_DIR}/server"
    cd / && rm -rf /tmp/llama-build
    log "llama.cpp built successfully."
fi

log "Setup complete."
