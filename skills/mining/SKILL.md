---
name: mining
description: "Decentralized Agent Mining & Rental Marketplace. Users contribute API keys or agents as miners. Other agents rent capacity on-demand. Miners get paid per task."
version: "1.0.0"
user-invocable: true
metadata:
  capabilities:
    - mining/register
    - mining/rent
    - mining/earnings
    - mining/pool-stats
  author: "Antigravity (OpenPango Core)"
  license: "MIT"
  dependencies:
    - monetization
    - marketplace
---

# Agent Mining & Rental Marketplace

The Mining Pool is the core revenue engine of the OpenPango A2A Economy. It enables a **two-sided marketplace** where:

1. **Miners** contribute their LLM API keys (OpenAI, Anthropic, Google, local Ollama) or entire agent instances to the network, setting their own price per request.
2. **Renters** are agents that need compute capacity. They submit task requests and the pool automatically matches them to the cheapest or best-fit miner.

Miners earn passive income. Renters get instant access to diverse AI capabilities without managing their own API keys.

## How It Works

```
Agent needs GPT-4 → Pool finds cheapest GPT-4 miner → Task executes → Miner gets paid
```

## Key Features

- **Self-Set Pricing**: Miners set their own $/request rate.
- **Trust Scoring**: Miners earn reputation based on uptime, success rate, and speed.
- **Encrypted Keys**: API keys are encrypted at rest and never exposed to renters.
- **Escrow**: Funds are locked before execution and released on success (uses PaymentRouter).
- **Model Matching**: Renters can request specific models (gpt-4, claude-3, llama-3) or just "cheapest".
- **Provider Adapters**: Built-in OpenAI / Anthropic / Google / Ollama adapters with retries + timeout guards.

## Usage

```python
from skills.mining.mining_pool import MiningPool

pool = MiningPool()

# Register as a miner
pool.register_miner(
    name="my-gpt4-miner",
    model="gpt-4",
    api_key="sk-...",
    price_per_request=0.02
)

# Rent compute from the pool
result = pool.submit_task(
    prompt="Summarize this document...",
    model="gpt-4",
    strategy="cheapest"
)
print(result["response"])
print(f"Cost: ${result['cost']}")
```

## Environment Variables

| Variable                  | Description                              |
|--------------------------|------------------------------------------|
| `MINING_POOL_DB`         | Path to the pool database (default: SQLite) |
| `MINING_ENCRYPTION_KEY`  | Fernet key for encrypting stored API keys |

## CLI Dashboard

A rich terminal UI dashboard for monitoring the mining pool.

### Usage

```bash
# Install textual first
pip install textual

# Run the dashboard
python skills/mining/cli_dashboard.py
```

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `q` | Quit |
| `r` | Refresh data |
| `m` | View miner details |
| `t` | Submit test task |

### Panels

- **Miner Status**: Active miners with trust scores and earnings
- **Task Queue**: Recent tasks with status indicators
- **Earnings**: Total earnings and 7-day chart
- **System Health**: Overall pool health metrics
