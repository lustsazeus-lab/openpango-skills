#!/usr/bin/env python3
"""
wallet.py - Web3 & Crypto Native Skill for OpenPango Agents.

Provides wallet management, balance checking, transaction signing,
and smart contract interaction for EVM-compatible chains.
Falls back to mock mode when no RPC URL or private key is configured.
"""

import os
import json
import hashlib
import secrets
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger("Web3Agent")


class Web3Agent:
    """
    Secure Web3 wallet and transaction agent.
    Supports any EVM-compatible chain. Falls back to mock mode
    when WEB3_RPC_URL is not set.
    """

    def __init__(self):
        self.rpc_url = os.getenv("WEB3_RPC_URL", "")
        self.private_key = os.getenv("AGENT_WALLET_PRIVATE_KEY", "")
        self.chain_id = int(os.getenv("WEB3_CHAIN_ID", "1"))
        self._mock = not bool(self.rpc_url)

        if self._mock:
            logger.warning("No WEB3_RPC_URL set. Running in MOCK mode.")
            self._mock_address = "0x" + secrets.token_hex(20)
            self._mock_balances: Dict[str, float] = {self._mock_address: 10.0}
            self._mock_nonce = 0
            self._mock_txs: List[Dict] = []
        else:
            logger.info(f"Connected to RPC: {self.rpc_url[:30]}... (Chain ID: {self.chain_id})")

    # ─── Wallet ──────────────────────────────────────────────

    def get_address(self) -> Dict[str, str]:
        """Get the agent's wallet address."""
        if self._mock:
            return {"address": self._mock_address, "chain_id": self.chain_id, "mock": True}

        # In production: derive address from private key using eth_account
        return {"address": "0x_LIVE_ADDRESS_FROM_KEY", "chain_id": self.chain_id}

    def generate_wallet(self) -> Dict[str, str]:
        """Generate a new wallet (keypair)."""
        private_key = "0x" + secrets.token_hex(32)
        # Mock address derivation (in production: use eth_account)
        address = "0x" + hashlib.sha256(private_key.encode()).hexdigest()[:40]
        logger.info(f"Generated new wallet: {address}")
        return {
            "address": address,
            "private_key": private_key,
            "warning": "NEVER share your private key. Store it securely."
        }

    # ─── Balances ────────────────────────────────────────────

    def get_balance(self, address: str) -> Dict[str, Any]:
        """Get ETH balance for an address."""
        if self._mock:
            bal = self._mock_balances.get(address, 0.0)
            return {
                "address": address,
                "eth": bal,
                "wei": int(bal * 1e18),
                "chain_id": self.chain_id,
                "mock": True
            }

        # Production: web3.eth.get_balance(address)
        return {"error": "Live RPC not implemented in this version"}

    def get_token_balance(self, address: str, token_contract: str,
                          decimals: int = 18) -> Dict[str, Any]:
        """Get ERC-20 token balance."""
        if self._mock:
            mock_balance = 1000.0  # Simulated token balance
            return {
                "address": address,
                "token_contract": token_contract,
                "balance": mock_balance,
                "decimals": decimals,
                "mock": True
            }

        return {"error": "Live RPC not implemented in this version"}

    # ─── Transactions ────────────────────────────────────────

    def send_transaction(self, to: str, value_eth: float,
                         gas_limit: int = 21000, data: str = "") -> Dict[str, Any]:
        """Sign and send an ETH transaction."""
        if self._mock:
            tx_hash = "0x" + secrets.token_hex(32)
            self._mock_nonce += 1

            # Simulate balance deduction
            sender = self._mock_address
            self._mock_balances[sender] = self._mock_balances.get(sender, 0) - value_eth
            self._mock_balances[to] = self._mock_balances.get(to, 0) + value_eth

            tx_record = {
                "hash": tx_hash,
                "from": sender,
                "to": to,
                "value_eth": value_eth,
                "gas_limit": gas_limit,
                "nonce": self._mock_nonce,
                "chain_id": self.chain_id,
                "status": "confirmed",
                "block": 19000000 + self._mock_nonce,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "mock": True
            }
            self._mock_txs.append(tx_record)
            logger.info(f"[MOCK TX] {sender[:10]}… → {to[:10]}… | {value_eth} ETH | Hash: {tx_hash[:16]}…")
            return tx_record

        return {"error": "Live RPC not implemented in this version"}

    def get_transaction(self, tx_hash: str) -> Dict[str, Any]:
        """Get transaction details by hash."""
        if self._mock:
            for tx in self._mock_txs:
                if tx["hash"] == tx_hash:
                    return tx
            return {"error": f"Transaction {tx_hash} not found"}

        return {"error": "Live RPC not implemented in this version"}

    # ─── Smart Contracts ─────────────────────────────────────

    def call_contract(self, address: str, abi: List[Dict],
                      function: str, args: List = None) -> Dict[str, Any]:
        """Call a read-only smart contract function."""
        args = args or []
        if self._mock:
            logger.info(f"[MOCK CONTRACT] {address[:10]}….{function}({args})")
            return {
                "contract": address,
                "function": function,
                "args": args,
                "result": f"mock_result_for_{function}",
                "mock": True
            }

        return {"error": "Live RPC not implemented in this version"}

    def write_contract(self, address: str, abi: List[Dict],
                       function: str, args: List = None,
                       value_eth: float = 0) -> Dict[str, Any]:
        """Execute a state-changing smart contract function."""
        args = args or []
        if self._mock:
            tx_hash = "0x" + secrets.token_hex(32)
            self._mock_nonce += 1
            logger.info(f"[MOCK CONTRACT WRITE] {address[:10]}….{function}({args}) → {tx_hash[:16]}…")
            return {
                "hash": tx_hash,
                "contract": address,
                "function": function,
                "args": args,
                "value_eth": value_eth,
                "status": "confirmed",
                "mock": True
            }

        return {"error": "Live RPC not implemented in this version"}

    # ─── Transaction History ─────────────────────────────────

    def get_history(self, limit: int = 10) -> List[Dict]:
        """Get recent transaction history."""
        if self._mock:
            return self._mock_txs[-limit:]
        return []

    # ─── Gas Estimation ──────────────────────────────────────

    def estimate_gas(self, to: str, value_eth: float = 0, data: str = "") -> Dict[str, Any]:
        """Estimate gas for a transaction."""
        if self._mock:
            # Standard ETH transfer = 21000 gas
            gas = 21000 if not data else 65000
            gas_price_gwei = 25.0  # Simulated
            cost_eth = (gas * gas_price_gwei * 1e-9)
            return {
                "gas_estimate": gas,
                "gas_price_gwei": gas_price_gwei,
                "estimated_cost_eth": round(cost_eth, 8),
                "mock": True
            }

        return {"error": "Live RPC not implemented in this version"}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="OpenPango Web3 Agent")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # Balance
    bal = sub.add_parser("balance", help="Check ETH balance")
    bal.add_argument("address")

    # Send
    send = sub.add_parser("send", help="Send ETH")
    send.add_argument("--to", required=True)
    send.add_argument("--value", type=float, required=True, help="Amount in ETH")

    # Generate wallet
    sub.add_parser("generate", help="Generate a new wallet")

    # Gas estimate
    gas = sub.add_parser("gas", help="Estimate gas")
    gas.add_argument("--to", required=True)
    gas.add_argument("--value", type=float, default=0)

    # History
    hist = sub.add_parser("history", help="Transaction history")
    hist.add_argument("--limit", type=int, default=10)

    args = parser.parse_args()
    agent = Web3Agent()

    if args.cmd == "balance":
        result = agent.get_balance(args.address)
    elif args.cmd == "send":
        result = agent.send_transaction(to=args.to, value_eth=args.value)
    elif args.cmd == "generate":
        result = agent.generate_wallet()
    elif args.cmd == "gas":
        result = agent.estimate_gas(to=args.to, value_eth=args.value)
    elif args.cmd == "history":
        result = agent.get_history(limit=args.limit)

    print(json.dumps(result, indent=2))
