#!/usr/bin/env bash
# AegisNova OS — ai-shell CLI wrapper
# Sends queries to the local llama.cpp server and prints responses.
# Usage: ai-shell "your question here"
set -euo pipefail

LLM_ENDPOINT="${LLM_ENDPOINT:-http://127.0.0.1:8080/completion}"
PROMPT="${*:?Usage: ai-shell \"your question\"}"

# Check if server is running
if ! curl -sf "${LLM_ENDPOINT%/completion}/health" &>/dev/null; then
    echo "⚠️  LLM server not running. Start with: systemctl start ai-shell"
    exit 1
fi

# Send query
RESPONSE=$(curl -sf "${LLM_ENDPOINT}" \
    -H "Content-Type: application/json" \
    -d "{
        \"prompt\": \"You are a cybersecurity expert. Answer concisely.\n\nQ: ${PROMPT}\nA:\",
        \"n_predict\": 512,
        \"temperature\": 0.3,
        \"stop\": [\"Q:\", \"\\n\\n\\n\"]
    }" 2>/dev/null)

if [[ -n "${RESPONSE}" ]]; then
    echo "${RESPONSE}" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(data.get('content', 'No response.').strip())
except:
    print(sys.stdin.read())
" 2>/dev/null || echo "${RESPONSE}"
else
    echo "❌ No response from LLM server."
fi
