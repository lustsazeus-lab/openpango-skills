---
name: web3
description: "Secure wallet management, transaction signing, token balances, and smart contract interaction for EVM-compatible chains."
version: "1.0.0"
user-invocable: true
metadata:
  capabilities:
    - web3/wallet
    - web3/transactions
    - web3/contracts
    - web3/balances
  author: "Antigravity (OpenPango Core)"
  license: "MIT"
---

# Web3 & Crypto Native Skill

Enables OpenPango agents to interact with blockchain networks natively. Agents can check balances, send transactions, and call smart contracts on any EVM-compatible chain (Ethereum, Polygon, Base, Arbitrum, etc).

## Features

- **Wallet Management**: Generate or import wallets, check balances (ETH + ERC-20 tokens)
- **Transaction Signing**: Sign and broadcast transactions securely
- **Smart Contract Calls**: Read from and write to deployed contracts via ABI
- **Multi-Chain**: Supports any EVM chain via configurable RPC endpoints
- **Mock Mode**: Full simulation when no RPC URL or private key is set

## Usage

```python
from skills.web3.wallet import Web3Agent

agent = Web3Agent()

# Check ETH balance
balance = agent.get_balance("0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")
print(f"Balance: {balance['eth']} ETH")

# Send a transaction
tx = agent.send_transaction(
    to="0x...",
    value_eth=0.01,
    gas_limit=21000
)
print(f"TX Hash: {tx['hash']}")

# Read a smart contract
result = agent.call_contract(
    address="0x...",
    abi=[...],
    function="balanceOf",
    args=["0x..."]
)
```

## Environment Variables

| Variable                   | Description                          |
|---------------------------|--------------------------------------|
| `WEB3_RPC_URL`            | RPC endpoint (e.g., Alchemy, Infura) |
| `AGENT_WALLET_PRIVATE_KEY`| Private key for signing transactions |
| `WEB3_CHAIN_ID`           | Chain ID (default: 1 for mainnet)    |
