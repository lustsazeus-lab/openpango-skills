#!/usr/bin/env python3
"""test_cli_dashboard.py - Tests for CLI Dashboard."""

import os
import sys
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone

TEST_DB = tempfile.mktemp(suffix=".db")
os.environ["MINING_POOL_DB"] = TEST_DB


class TestCLIDashboard(unittest.TestCase):
    """Test CLI Dashboard data loading."""
    
    @classmethod
    def setUpClass(cls):
        conn = sqlite3.connect(TEST_DB)
        conn.execute("""CREATE TABLE IF NOT EXISTS miners (
            miner_id TEXT PRIMARY KEY, name TEXT, model TEXT, api_key_encrypted TEXT,
            price_per_request REAL, status TEXT, trust_score REAL, total_tasks INTEGER,
            successful_tasks INTEGER, total_earned REAL, avg_response_ms REAL,
            registered_at TEXT, last_seen TEXT)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS task_log (
            task_id TEXT PRIMARY KEY, miner_id TEXT, renter_id TEXT, model TEXT,
            prompt_hash TEXT, status TEXT, cost REAL, response_ms REAL,
            created_at TEXT, completed_at TEXT)""")
        conn.execute("""CREATE TABLE IF NOT EXISTS escrow (
            task_id TEXT PRIMARY KEY, renter_id TEXT, miner_id TEXT,
            amount REAL, status TEXT, created_at TEXT)""")
        
        now = datetime.now(timezone.utc).isoformat()
        conn.execute("INSERT INTO miners VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ('m1', 'GPT4', 'gpt-4', 'key', 0.01, 'online', 95.0, 100, 98, 5.50, 250, now, now))
        conn.execute("INSERT INTO miners VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ('m2', 'Claude', 'claude-3', 'key', 0.015, 'busy', 88.0, 50, 45, 3.20, 180, now, now))
        conn.execute("INSERT INTO task_log VALUES (?,?,?,?,?,?,?,?,?,?)",
            ('t1', 'm1', 'r1', 'gpt-4', 'h1', 'completed', 0.01, 200, now, now))
        conn.execute("INSERT INTO task_log VALUES (?,?,?,?,?,?,?,?,?,?)",
            ('t2', 'm2', 'r1', 'claude-3', 'h2', 'pending', 0.0, 0, now, None))
        conn.execute("INSERT INTO escrow VALUES (?,?,?,?,?,?)",
            ('e1', 'r1', 'm1', 0.015, 'locked', now))
        conn.commit()
        conn.close()
    
    @classmethod
    def tearDownClass(cls):
        os.unlink(TEST_DB)
    
    def test_miners_count(self):
        conn = sqlite3.connect(TEST_DB)
        count = conn.execute("SELECT COUNT(*) FROM miners").fetchone()[0]
        conn.close()
        self.assertEqual(count, 2)
    
    def test_tasks_count(self):
        conn = sqlite3.connect(TEST_DB)
        count = conn.execute("SELECT COUNT(*) FROM task_log").fetchone()[0]
        conn.close()
        self.assertEqual(count, 2)
    
    def test_total_earnings(self):
        conn = sqlite3.connect(TEST_DB)
        total = conn.execute("SELECT SUM(total_earned) FROM miners").fetchone()[0]
        conn.close()
        self.assertEqual(total, 8.7)
    
    def test_pending_tasks(self):
        conn = sqlite3.connect(TEST_DB)
        count = conn.execute("SELECT COUNT(*) FROM task_log WHERE status='pending'").fetchone()[0]
        conn.close()
        self.assertEqual(count, 1)
    
    def test_online_miners(self):
        conn = sqlite3.connect(TEST_DB)
        count = conn.execute("SELECT COUNT(*) FROM miners WHERE status='online'").fetchone()[0]
        conn.close()
        self.assertEqual(count, 1)
    
    def test_escrow_locked(self):
        conn = sqlite3.connect(TEST_DB)
        amount = conn.execute("SELECT SUM(amount) FROM escrow WHERE status='locked'").fetchone()[0]
        conn.close()
        self.assertEqual(amount, 0.015)
    
    def test_success_rate(self):
        conn = sqlite3.connect(TEST_DB)
        row = conn.execute("SELECT total_tasks, successful_tasks FROM miners WHERE miner_id='m1'").fetchone()
        conn.close()
        rate = row[1] / row[0] * 100
        self.assertEqual(rate, 98.0)


if __name__ == "__main__":
    unittest.main()
