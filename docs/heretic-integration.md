# Heretic Integration for AegisNova OS

This integration adds [Heretic](https://github.com/p-e-w/heretic) — fully automatic censorship removal for language models — into AegisNova OS.

## What is Heretic?

Heretic removes "safety alignment" (censorship) from transformer-based language models without expensive retraining. It uses directional ablation (abliteration) combined with automatic parameter optimization.

## How it works in AegisNova OS

1. **Installation**: Heretic is automatically installed during OS build via pip
2. **Auto-decensoring**: On first boot, the system attempts to decensor the default Gemma-2B model
3. **Dynamic selection**: AI agents automatically use the decensored model if available
4. **Fallback**: If decensoring fails or is incomplete, agents fall back to the base model

## Services

- `heretic-decensor.service`: One-shot service that runs heretic on the base model
- `ai-shell.service`: Now checks for decensored model before starting llama.cpp server

## Usage

### Manual decensoring

```bash
# Decensor any model
/opt/aegisnova/heretic/decensor-model.sh input-model.gguf output-model.gguf

# Auto-decensor default model
/opt/aegisnova/heretic/auto-decensor.sh
```

### Check status

```bash
# Check if decensored model exists
ls -la /opt/aegisnova/models/decensored/

# View heretic logs
journalctl -u heretic-decensor -f

# Check which model AI is using
journalctl -u ai-shell | grep "Using"
```

## Technical Details

- **Location**: `/opt/aegisnova/heretic/`
- **Python venv**: `/opt/aegisnova/heretic/venv/`
- **Decensored models**: `/opt/aegisnova/models/decensored/`
- **Dependencies**: PyTorch, transformers, heretic-llm

## Requirements

- GPU with CUDA support recommended (decensoring can take 30-90 min on GPU)
- Without GPU: decensoring may take several hours or fail on large models
- Sufficient disk space (~2-3x model size for intermediate files)

## Security Note

Decensored models have fewer restrictions and may generate content that could be considered harmful. Use responsibly and only in authorized security testing contexts.
