#!/usr/bin/env python3
"""
mining_pool.py - Agent Mining & Rental Marketplace.

The revenue engine of the OpenPango A2A Economy. Users contribute
their LLM API keys or agent instances as "miners" and earn passive
income when other agents rent their capacity.
"""

import os
import json
import uuid
import hashlib
import sqlite3
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from base64 import b64encode, b64decode

from skills.mining.adapters import AdapterExecutionError, execute_inference, infer_provider

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger("MiningPool")

DB_PATH = os.getenv("MINING_POOL_DB", str(Path.home() / ".openclaw" / "mining_pool.db"))


def _obfuscate_key(key: str) -> str:
    """Simple obfuscation for API keys at rest (use Fernet in production)."""
    return b64encode(key.encode()).decode()


def _deobfuscate_key(token: str) -> str:
    """Reverse obfuscation."""
    return b64decode(token.encode()).decode()


class MinerRegistry:
    """Manages miner registrations, trust scores, and status."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS miners (
                    miner_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    model TEXT NOT NULL,
                    api_key_encrypted TEXT NOT NULL,
                    price_per_request REAL NOT NULL,
                    status TEXT DEFAULT 'online',
                    trust_score REAL DEFAULT 100.0,
                    total_tasks INTEGER DEFAULT 0,
                    successful_tasks INTEGER DEFAULT 0,
                    total_earned REAL DEFAULT 0.0,
                    avg_response_ms REAL DEFAULT 0.0,
                    registered_at TEXT NOT NULL,
                    last_seen TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_log (
                    task_id TEXT PRIMARY KEY,
                    miner_id TEXT NOT NULL,
                    renter_id TEXT NOT NULL,
                    model TEXT,
                    prompt_hash TEXT,
                    status TEXT DEFAULT 'pending',
                    cost REAL DEFAULT 0.0,
                    response_ms REAL DEFAULT 0.0,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    FOREIGN KEY (miner_id) REFERENCES miners(miner_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS escrow (
                    task_id TEXT PRIMARY KEY,
                    renter_id TEXT NOT NULL,
                    miner_id TEXT NOT NULL,
                    amount REAL NOT NULL,
                    status TEXT DEFAULT 'locked',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (task_id) REFERENCES task_log(task_id)
                )
            """)

    def register(self, name: str, model: str, api_key: str,
                 price_per_request: float, miner_id: str = None) -> Dict:
        """Register a new miner in the pool."""
        miner_id = miner_id or f"miner_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        encrypted_key = _obfuscate_key(api_key)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO miners
                (miner_id, name, model, api_key_encrypted, price_per_request,
                 status, trust_score, total_tasks, successful_tasks,
                 total_earned, avg_response_ms, registered_at, last_seen)
                VALUES (?, ?, ?, ?, ?, 'online', 100.0, 0, 0, 0.0, 0.0, ?, ?)
            """, (miner_id, name, model, encrypted_key, price_per_request, now, now))

        logger.info(f"Miner registered: {name} ({model}) @ ${price_per_request}/req → ID: {miner_id}")
        return {
            "status": "registered",
            "miner_id": miner_id,
            "name": name,
            "model": model,
            "price_per_request": price_per_request,
        }

    def get_miners(self, model: str = None, status: str = "online") -> List[Dict]:
        """List available miners, optionally filtered by model and status."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM miners WHERE status = ?"
            params = [status]
            if model:
                query += " AND model = ?"
                params.append(model)
            query += " ORDER BY price_per_request ASC"
            rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

    def update_trust(self, miner_id: str, success: bool, response_ms: float):
        """Update miner trust score and stats after a task."""
        with sqlite3.connect(self.db_path) as conn:
            miner = conn.execute("SELECT * FROM miners WHERE miner_id = ?", (miner_id,)).fetchone()
            if not miner:
                return

            total = miner[7] + 1  # total_tasks
            successful = miner[8] + (1 if success else 0)  # successful_tasks
            
            # Trust = weighted combination of success rate and response time
            success_rate = (successful / total) * 100 if total > 0 else 100
            speed_penalty = min(response_ms / 10000, 20)  # Max 20 point penalty for slow responses
            trust = max(0, min(100, success_rate - speed_penalty))

            # Running average of response time
            old_avg = miner[10]  # avg_response_ms
            new_avg = ((old_avg * (total - 1)) + response_ms) / total if total > 0 else response_ms

            conn.execute("""
                UPDATE miners SET 
                    total_tasks = ?, successful_tasks = ?,
                    trust_score = ?, avg_response_ms = ?,
                    last_seen = ?
                WHERE miner_id = ?
            """, (total, successful, round(trust, 2), round(new_avg, 2),
                  datetime.now(timezone.utc).isoformat(), miner_id))

    def get_earnings(self, miner_id: str) -> Dict:
        """Get a miner's earnings summary."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT total_earned, total_tasks, successful_tasks, trust_score FROM miners WHERE miner_id = ?",
                (miner_id,)
            ).fetchone()
        if not row:
            return {"error": "Miner not found"}
        return {
            "miner_id": miner_id,
            "total_earned": row[0],
            "total_tasks": row[1],
            "successful_tasks": row[2],
            "trust_score": row[3],
        }


class TaskRouter:
    """Routes task requests to the best available miner."""

    STRATEGIES = ("cheapest", "fastest", "best_trust", "specific_model")

    def __init__(self, registry: MinerRegistry):
        self.registry = registry

    def find_miner(self, model: str = None, strategy: str = "cheapest") -> Optional[Dict]:
        """Find the best miner for a given request."""
        miners = self.registry.get_miners(model=model)
        if not miners:
            return None

        if strategy == "cheapest":
            return min(miners, key=lambda m: m["price_per_request"])
        elif strategy == "fastest":
            return min(miners, key=lambda m: m.get("avg_response_ms", float("inf")))
        elif strategy == "best_trust":
            return max(miners, key=lambda m: m.get("trust_score", 0))
        else:
            return miners[0] if miners else None


class MiningPool:
    """
    The main orchestrator. Handles the full lifecycle:
    Register → Match → Lock Escrow → Execute → Pay → Update Trust
    """

    def __init__(self, db_path: str = DB_PATH):
        self.registry = MinerRegistry(db_path=db_path)
        self.router = TaskRouter(self.registry)
        self.db_path = db_path

    def register_miner(self, name: str, model: str, api_key: str,
                       price_per_request: float, miner_id: str = None) -> Dict:
        """Register a new miner."""
        return self.registry.register(name, model, api_key, price_per_request, miner_id)

    def get_pool_stats(self) -> Dict:
        """Get overall pool statistics."""
        with sqlite3.connect(self.db_path) as conn:
            total_miners = conn.execute("SELECT COUNT(*) FROM miners").fetchone()[0]
            online_miners = conn.execute("SELECT COUNT(*) FROM miners WHERE status = 'online'").fetchone()[0]
            total_tasks = conn.execute("SELECT COUNT(*) FROM task_log").fetchone()[0]
            total_revenue = conn.execute("SELECT COALESCE(SUM(cost), 0) FROM task_log WHERE status = 'completed'").fetchone()[0]
            models = conn.execute("SELECT DISTINCT model FROM miners WHERE status = 'online'").fetchall()

        return {
            "total_miners": total_miners,
            "online_miners": online_miners,
            "total_tasks_processed": total_tasks,
            "total_revenue": round(total_revenue, 4),
            "available_models": [m[0] for m in models],
        }

    def submit_task(self, prompt: str, model: str = None,
                    strategy: str = "cheapest", renter_id: str = None) -> Dict:
        """
        Submit a task to the mining pool.
        
        1. Find the best miner
        2. Lock funds in escrow
        3. Execute the task via provider adapters
        4. Release escrow to miner
        5. Update trust scores
        """
        renter_id = renter_id or f"renter_{uuid.uuid4().hex[:8]}"
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()

        # Step 1: Find miner
        miner = self.router.find_miner(model=model, strategy=strategy)
        if not miner:
            return {"error": f"No miners available for model={model}, strategy={strategy}"}

        miner_id = miner["miner_id"]
        cost = miner["price_per_request"]
        prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:16]

        # Step 2: Lock escrow
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO task_log (task_id, miner_id, renter_id, model, prompt_hash, status, cost, created_at)
                VALUES (?, ?, ?, ?, ?, 'executing', ?, ?)
            """, (task_id, miner_id, renter_id, miner.get("model"), prompt_hash, cost, now))
            conn.execute("""
                INSERT INTO escrow (task_id, renter_id, miner_id, amount, status, created_at)
                VALUES (?, ?, ?, ?, 'locked', ?)
            """, (task_id, renter_id, miner_id, cost, now))

        logger.info(f"Task {task_id} → Miner {miner['name']} @ ${cost}/req (escrow locked)")

        # Step 3: Execute via provider adapter
        start_ms = time.time() * 1000
        provider = infer_provider(miner.get("model"))
        api_key = _deobfuscate_key(miner.get("api_key_encrypted", ""))

        success = False
        response_text = ""
        error_message = None

        try:
            response_text = execute_inference(
                provider=provider,
                prompt=prompt,
                model=miner.get("model"),
                api_key=api_key,
                timeout=30.0,
                max_retries=2,
            )
            success = True
        except AdapterExecutionError as exc:
            error_message = str(exc)
            logger.error(f"Task {task_id} failed during provider execution: {error_message}")

        response_ms = (time.time() * 1000) - start_ms

        # Step 4: Settle escrow and task status
        completed_at = datetime.now(timezone.utc).isoformat()
        task_status = "completed" if success else "failed"
        escrow_status = "released" if success else "refunded"

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE task_log SET status = ?, response_ms = ?, completed_at = ? WHERE task_id = ?",
                (task_status, response_ms, completed_at, task_id),
            )
            conn.execute("UPDATE escrow SET status = ? WHERE task_id = ?", (escrow_status, task_id))
            if success:
                conn.execute(
                    "UPDATE miners SET total_earned = total_earned + ? WHERE miner_id = ?",
                    (cost, miner_id),
                )

        # Step 5: Update trust
        self.registry.update_trust(miner_id, success, response_ms)

        if success:
            logger.info(f"Task {task_id} completed. Miner {miner['name']} earned ${cost}")
        else:
            logger.info(f"Task {task_id} failed. Escrow refunded to renter.")

        result = {
            "task_id": task_id,
            "miner": miner["name"],
            "miner_id": miner_id,
            "model": miner.get("model"),
            "provider": provider,
            "cost": cost,
            "response_ms": round(response_ms, 2),
            "status": task_status,
        }

        if success:
            result["response"] = response_text
        else:
            result["error"] = error_message or "Task execution failed"

        return result

    def get_earnings(self, miner_id: str) -> Dict:
        """Get earnings for a miner."""
        return self.registry.get_earnings(miner_id)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="OpenPango Mining Pool")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # Register miner
    reg = sub.add_parser("register", help="Register as a miner")
    reg.add_argument("--name", required=True)
    reg.add_argument("--model", required=True, help="e.g., gpt-4, claude-3, llama-3")
    reg.add_argument("--api-key", required=True)
    reg.add_argument("--price", type=float, required=True, help="Price per request in USD")

    # Submit task
    task = sub.add_parser("submit", help="Submit a task to the pool")
    task.add_argument("--prompt", required=True)
    task.add_argument("--model", help="Specific model to use")
    task.add_argument("--strategy", default="cheapest", choices=["cheapest", "fastest", "best_trust"])

    # Pool stats
    sub.add_parser("stats", help="Show pool statistics")

    # Miner earnings
    earn = sub.add_parser("earnings", help="Check miner earnings")
    earn.add_argument("--miner-id", required=True)

    # List miners
    ls = sub.add_parser("list", help="List available miners")
    ls.add_argument("--model", help="Filter by model")

    args = parser.parse_args()
    pool = MiningPool()

    if args.cmd == "register":
        result = pool.register_miner(args.name, args.model, args.api_key, args.price)
    elif args.cmd == "submit":
        result = pool.submit_task(args.prompt, model=args.model, strategy=args.strategy)
    elif args.cmd == "stats":
        result = pool.get_pool_stats()
    elif args.cmd == "earnings":
        result = pool.get_earnings(args.miner_id)
    elif args.cmd == "list":
        result = pool.registry.get_miners(model=getattr(args, 'model', None))

    print(json.dumps(result, indent=2))
