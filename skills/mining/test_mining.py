import os
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from skills.mining.adapters import AdapterExecutionError
from skills.mining.mining_pool import MiningPool


class TestMiningPool(unittest.TestCase):

    def setUp(self):
        self.db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.db_file.name
        self.db_file.close()

        self.execute_patch = patch(
            "skills.mining.mining_pool.execute_inference",
            return_value="mocked adapter response",
        )
        self.mock_execute = self.execute_patch.start()

        self.pool = MiningPool(db_path=self.db_path)

    def tearDown(self):
        self.execute_patch.stop()
        os.unlink(self.db_path)

    # ─── Registration ────────────────────────────────────────

    def test_register_miner(self):
        result = self.pool.register_miner(
            name="TestGPT", model="gpt-4",
            api_key="sk-test-123", price_per_request=0.05
        )
        self.assertEqual(result["status"], "registered")
        self.assertEqual(result["model"], "gpt-4")
        self.assertEqual(result["price_per_request"], 0.05)

    def test_list_miners(self):
        self.pool.register_miner("Miner1", "gpt-4", "sk-1", 0.02)
        self.pool.register_miner("Miner2", "claude-3", "sk-2", 0.01)
        miners = self.pool.registry.get_miners()
        self.assertEqual(len(miners), 2)

    def test_list_miners_by_model(self):
        self.pool.register_miner("GPT", "gpt-4", "sk-1", 0.02)
        self.pool.register_miner("Claude", "claude-3", "sk-2", 0.01)
        gpt_miners = self.pool.registry.get_miners(model="gpt-4")
        self.assertEqual(len(gpt_miners), 1)
        self.assertEqual(gpt_miners[0]["name"], "GPT")

    # ─── Task Routing ────────────────────────────────────────

    def test_cheapest_routing(self):
        self.pool.register_miner("Expensive", "gpt-4", "sk-1", 0.10)
        self.pool.register_miner("Cheap", "gpt-4", "sk-2", 0.01)
        miner = self.pool.router.find_miner(model="gpt-4", strategy="cheapest")
        self.assertEqual(miner["name"], "Cheap")

    def test_no_miners_available(self):
        miner = self.pool.router.find_miner(model="nonexistent")
        self.assertIsNone(miner)

    # ─── Task Execution & Escrow ─────────────────────────────

    def test_submit_task(self):
        self.pool.register_miner("Worker", "gpt-4", "sk-1", 0.03)
        result = self.pool.submit_task(
            prompt="What is 2+2?",
            model="gpt-4",
            strategy="cheapest"
        )
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["cost"], 0.03)
        self.assertIn("response", result)
        self.assertEqual(result["provider"], "openai")

    def test_submit_task_no_miner(self):
        result = self.pool.submit_task(prompt="Hello", model="nonexistent")
        self.assertIn("error", result)

    def test_escrow_released_on_success(self):
        self.pool.register_miner("Worker", "gpt-4", "sk-1", 0.05, miner_id="miner_test1")
        result = self.pool.submit_task(prompt="Test", model="gpt-4")

        with sqlite3.connect(self.db_path) as conn:
            escrow = conn.execute(
                "SELECT status FROM escrow WHERE task_id = ?", (result["task_id"],)
            ).fetchone()
        self.assertEqual(escrow[0], "released")

    def test_escrow_refunded_on_failure(self):
        self.mock_execute.side_effect = AdapterExecutionError("provider failed", retryable=False)
        self.pool.register_miner("Worker", "gpt-4", "sk-1", 0.05, miner_id="miner_refund")

        result = self.pool.submit_task(prompt="Test", model="gpt-4")
        self.assertEqual(result["status"], "failed")
        self.assertIn("error", result)

        with sqlite3.connect(self.db_path) as conn:
            escrow = conn.execute(
                "SELECT status FROM escrow WHERE task_id = ?", (result["task_id"],)
            ).fetchone()
            earned = conn.execute(
                "SELECT total_earned FROM miners WHERE miner_id = ?", ("miner_refund",)
            ).fetchone()[0]

        self.assertEqual(escrow[0], "refunded")
        self.assertEqual(earned, 0.0)

    # ─── Earnings & Trust ────────────────────────────────────

    def test_miner_earnings_accumulate(self):
        self.pool.register_miner("Earner", "gpt-4", "sk-1", 0.02, miner_id="earner1")
        self.pool.submit_task(prompt="Task 1", model="gpt-4")
        self.pool.submit_task(prompt="Task 2", model="gpt-4")
        self.pool.submit_task(prompt="Task 3", model="gpt-4")

        earnings = self.pool.get_earnings("earner1")
        self.assertEqual(earnings["total_tasks"], 3)
        self.assertAlmostEqual(earnings["total_earned"], 0.06, places=4)

    def test_trust_score_updates(self):
        self.pool.register_miner("Trusted", "gpt-4", "sk-1", 0.01, miner_id="trust1")
        self.pool.submit_task(prompt="Hello", model="gpt-4")
        earnings = self.pool.get_earnings("trust1")
        self.assertGreater(earnings["trust_score"], 0)

    # ─── Pool Stats ──────────────────────────────────────────

    def test_pool_stats(self):
        self.pool.register_miner("M1", "gpt-4", "sk-1", 0.01)
        self.pool.register_miner("M2", "claude-3", "sk-2", 0.02)
        self.pool.submit_task(prompt="Go", strategy="cheapest")

        stats = self.pool.get_pool_stats()
        self.assertEqual(stats["total_miners"], 2)
        self.assertEqual(stats["online_miners"], 2)
        self.assertEqual(stats["total_tasks_processed"], 1)
        self.assertIn("gpt-4", stats["available_models"])


if __name__ == "__main__":
    unittest.main()
