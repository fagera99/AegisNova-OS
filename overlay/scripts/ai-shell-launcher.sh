#!/usr/bin/env bash
# AegisNova OS — AI Shell Launcher
# Dynamically selects decensored model if available
set -euo pipefail

MODELS_DIR="/opt/aegisnova/models"
DECENSORED_MODEL="${MODELS_DIR}/decensored/gemma-2b-heretic.gguf"
BASE_MODEL="${MODELS_DIR}/gemma-2b-Q4_K_M.gguf"
LLAMA_DIR="/opt/aegisnova/llama.cpp"

# Select model
if [[ -f "${DECENSORED_MODEL}" ]]; then
    export LLAMA_MODEL="${DECENSORED_MODEL}"
    echo "[ai-shell] Using DECENSORED model (Heretic)"
else
    export LLAMA_MODEL="${BASE_MODEL}"
    echo "[ai-shell] Using BASE model (censored)"
fi

# Run llama.cpp server
exec "${LLAMA_DIR}/server" \
    -m "${LLAMA_MODEL}" \
    --host 127.0.0.1 \
    --port "${LLAMA_PORT:-8080}" \
    -t "${LLAMA_THREADS:-4}" \
    -c "${LLAMA_CTX_SIZE:-4096}" \
    --log-disable
