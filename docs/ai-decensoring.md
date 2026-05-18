# AegisNova AI Decensoring System

## Overview

AegisNova OS features a **comprehensive AI decensoring system** that removes censorship ("safety alignment") from ALL AI model backends:

- ✅ **Local Models** (GGUF/HuggingFace) — Decensored via Heretic
- ✅ **OpenAI API** — Responses filtered through proxy
- ✅ **Anthropic API** — Responses filtered through proxy
- ✅ **HuggingFace Cloud** — Pre-decensored models auto-downloaded

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    AI Model Backends                      │
├─────────────┬─────────────┬─────────────┬───────────────┤
│   Local     │   OpenAI    │  Anthropic  │   HuggingFace │
│  (GGUF)     │    API      │    API      │    Cloud      │
└──────┬──────┴──────┬──────┴──────┬──────┴───────┬───────┘
       │             │             │              │
       ▼             ▼             ▼              ▼
┌─────────────────────────────────────────────────────────┐
│              Decensoring Layer                          │
├──────────────────┬──────────────────────────────────────┤
│ Heretic (Local)  │ AI Proxy (API Response Filtering)    │
│ - Abliteration   │ - Refusal pattern removal            │
│ - Auto-optimize  │ - Content rewriting                  │
└────────┬─────────┴──────────────┬───────────────────────┘
         │                        │
         ▼                        ▼
┌─────────────────────────────────────────────────────────┐
│              Unified Interface                           │
│         model_manager.py / ai-model CLI                 │
└─────────────────────────────────────────────────────────┘
```

## How It Works

### 1. Local Models (Primary)

**Default Model**: Gemma-2B (decensored)

On first boot:
1. System downloads base model (`gemma-2b-Q4_K_M.gguf`)
2. Heretic runs directional ablation (abliteration)
3. Decensored model saved to `/opt/aegisnova/models/decensored/`
4. AI services auto-use decensored version

```bash
# Check decensored model status
ls -la /opt/aegisnova/models/decensored/

# Manual decensor any model
/opt/aegisnova/heretic/decensor-model.sh input.gguf output.gguf
```

### 2. API Models (OpenAI/Anthropic)

When you set API keys, requests go through the **AI Decensoring Proxy**:

```
Your Query → AI Proxy (127.0.0.1:8081) → OpenAI/Anthropic API
                ↓
         Response with refusal patterns removed
                ↓
         Clean response to user
```

The proxy:
1. Intercepts API responses
2. Detects refusal patterns ("I'm sorry", "I cannot", etc.)
3. Removes or rewrites refusal content
4. Logs everything for audit

```bash
# Start proxy
systemctl start ai-proxy

# Test proxy
curl -X POST http://127.0.0.1:8081/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{"model":"gpt-4o","messages":[{"role":"user","content":"test"}]}'
```

### 3. HuggingFace Cloud

Pre-decensored models (marked `*-heretic`) can be downloaded directly:

```bash
# Available pre-decensored models
ai-model --list  # Shows cloud options

# These are community-verified decensored versions
# No processing needed - ready to use
```

## Configuration

### Model Configuration File

Location: `/etc/aegisnova/model-manager.conf`

```json
{
  "default_model": "local_gemma2b",
  "api_filtering": true,
  "proxy_enabled": true,
  "models": {
    "local_gemma2b": {
      "type": "local_gguf",
      "path": "/opt/aegisnova/models/decensored/gemma-2b-heretic.gguf",
      "decensored": true
    },
    "openai_gpt4": {
      "type": "api_openai",
      "endpoint": "http://127.0.0.1:8081",
      "decensored": true
    }
  }
}
```

### Environment Variables

File: `/etc/aegisnova/env`

```bash
# API Keys (optional)
OPENAI_API_KEY=sk-your-key
ANTHROPIC_API_KEY=sk-ant-your-key

# Local Model Paths
LLAMA_MODEL=/opt/aegisnova/models/decensored/gemma-2b-heretic.gguf

# Proxy Settings
AI_PROXY_HOST=127.0.0.1
AI_PROXY_PORT=8081
```

## Safety & Audit

### Automatic Logging

Every AI interaction is logged:

```bash
# All interactions
/var/log/aegisnova/ai/audit.log

# Safety events only
/var/log/aegisnova/ai/safety.log

# Proxy activity
/var/log/aegisnova/ai/proxy.log
```

### Safety Levels

Queries are classified:
- **SAFE**: General questions
- **CAUTION**: Security-related terms
- **DANGEROUS**: Multiple attack terms
- **FORBIDDEN**: Blocked (extreme cases)

### Audit Trail

Each query gets:
- Unique Audit ID
- User & timestamp
- Model used
- Safety classification
- Query/response hashes

```bash
# View recent audit
ai-model --audit-log

# Search by audit ID
grep "audit_id=abc123" /var/log/aegisnova/ai/audit.log
```

## Services

| Service | Purpose | Status |
|---------|---------|--------|
| `ai-shell` | Local LLM server | Auto-starts |
| `ai-proxy` | API decensoring proxy | Auto-starts |
| `heretic-decensor` | Model decensoring | Runs on boot |
| `ai-master-setup` | One-time configuration | Runs on first boot |

## Commands

```bash
# List all models and their decensoring status
ai-model --list

# Query (auto-selects decensored model)
ai-model "Your question here"

# Query specific model
ai-model -m openai_gpt4 "Your question"

# Skip safety checks (for authorized testing)
ai-model --skip-safety "Advanced query"

# View logs
journalctl -u ai-shell -f
journalctl -u ai-proxy -f
journalctl -u heretic-decensor -f
```

## Troubleshooting

### Local Model Not Decensored

```bash
# Check heretic status
systemctl status heretic-decensor
journalctl -u heretic-decensor --no-pager

# Manual decensoring
/opt/aegisnova/heretic/auto-decensor.sh
```

### API Proxy Not Working

```bash
# Check proxy status
systemctl status ai-proxy

# Test proxy manually
curl http://127.0.0.1:8081/health

# Restart
systemctl restart ai-proxy
```

### Model Manager Errors

```bash
# Check config
ai-model --list

# Verify config file
cat /etc/aegisnova/model-manager.conf | python3 -m json.tool

# Reset to defaults
cp /opt/aegisnova/model-manager.conf.example /etc/aegisnova/model-manager.conf
```

## Performance

| Model Type | Decensoring Time | VRAM Required |
|------------|------------------|---------------|
| Gemma-2B | 15-30 min | 4-6 GB |
| Llama-3-8B | 45-90 min | 8-12 GB |
| Qwen-3-4B | 30-60 min | 6-8 GB |
| API Models | Instant (proxy) | N/A |

## Security Warning

⚠️ **Decensored models have fewer restrictions.** They may generate content that could be considered harmful. Always:

1. Use only on systems you own or have written authorization to test
2. Log all interactions for accountability
3. Review outputs before executing any commands
4. Follow responsible disclosure practices
5. Comply with all applicable laws and regulations
