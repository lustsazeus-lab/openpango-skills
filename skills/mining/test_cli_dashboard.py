"""
Tests for CLI Dashboard.
"""

import os
import sys
import tempfile
import sqlite3
import subprocess
import json
from datetime import datetime, timedelta

import pytest


# Add skills to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


class TestCLIDashboard:
    """Test cases for CLI Dashboard."""
    
    def test_miner_dataclass(self):
        """Test Miner dataclass."""
        from skills.mining.cli_dashboard import Miner
        
        miner = Miner(
            id="1",
            name="test-miner",
            model="gpt-4",
            status="active",
            uptime=99.5,
            tasks_completed=100,
            earnings=25.50,
            price=0.02
        )
        
        assert miner.id == "1"
        assert miner.name == "test-miner"
        assert miner.model == "gpt-4"
        assert miner.status == "active"
        assert miner.uptime == 99.5
        assert miner.tasks_completed == 100
        assert miner.earnings == 25.50
        assert miner.price == 0.02
    
    def test_task_dataclass(self):
        """Test Task dataclass."""
        from skills.mining.cli_dashboard import Task
        
        started = datetime.now()
        completed = datetime.now() + timedelta(minutes=5)
        
        task = Task(
            id="t001",
            prompt="Test prompt",
            model="gpt-4",
            status="completed",
            started_at=started,
            completed_at=completed,
            cost=0.015
        )
        
        assert task.id == "t001"
        assert task.prompt == "Test prompt"
        assert task.model == "gpt-4"
        assert task.status == "completed"
        assert task.cost == 0.015
    
    def test_get_db_connection(self):
        """Test database connection creation."""
        from skills.mining.cli_dashboard import get_db_connection
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            
            # Create connection
            conn = get_db_connection(db_path)
            assert conn is not None
            
            # Verify database was created
            assert os.path.exists(db_path)
            
            conn.close()
    
    def test_list_miners_empty(self):
        """Test listing miners when database is empty."""
        from skills.mining.cli_dashboard import list_miners
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            
            # Create empty database
            conn = sqlite3.connect(db_path)
            conn.close()
            
            # Should return empty list
            miners = list_miners(db_path)
            assert miners == []
    
    def test_list_miners_with_data(self):
        """Test listing miners with data in database."""
        from skills.mining.cli_dashboard import list_miners, Miner
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            
            # Create database with miners table and data
            conn = sqlite3.connect(db_path)
            conn.execute("""
                CREATE TABLE miners (
                    id TEXT PRIMARY KEY,
                    name TEXT,
                    model TEXT,
                    status TEXT,
                    uptime REAL,
                    tasks_completed INTEGER,
                    earnings REAL,
                    price REAL
                )
            """)
            conn.execute("""
                INSERT INTO miners VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ("1", "test-miner", "gpt-4", "active", 99.5, 100, 25.50, 0.02))
            conn.commit()
            conn.close()
            
            # Should return the miner
            miners = list_miners(db_path)
            assert len(miners) == 1
            assert miners[0].name == "test-miner"
            assert miners[0].earnings == 25.50
    
    def test_list_tasks_empty(self):
        """Test listing tasks when database is empty."""
        from skills.mining.cli_dashboard import list_tasks
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            
            # Create empty database
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE tasks (id TEXT)")
            conn.close()
            
            # Should return empty list
            tasks = list_tasks(db_path)
            assert tasks == []
    
    def test_list_tasks_with_data(self):
        """Test listing tasks with data in database."""
        from skills.mining.cli_dashboard import list_tasks, Task
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            
            # Create database with tasks table and data
            conn = sqlite3.connect(db_path)
            conn.execute("""
                CREATE TABLE tasks (
                    id TEXT PRIMARY KEY,
                    prompt TEXT,
                    model TEXT,
                    status TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    cost REAL
                )
            """)
            started = datetime.now().isoformat()
            completed = (datetime.now() + timedelta(minutes=5)).isoformat()
            conn.execute("""
                INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?)
            """, ("t001", "Test task", "gpt-4", "completed", started, completed, 0.015))
            conn.commit()
            conn.close()
            
            # Should return the task
            tasks = list_tasks(db_path)
            assert len(tasks) == 1
            assert tasks[0].prompt == "Test task"
            assert tasks[0].cost == 0.015
    
    def test_get_earnings_summary(self):
        """Test getting earnings summary."""
        from skills.mining.cli_dashboard import get_earnings
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            
            # Create database
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE miners (earnings REAL)")
            conn.execute("CREATE TABLE tasks (completed_at TEXT, cost REAL)")
            conn.execute("INSERT INTO miners VALUES (100.50)")
            conn.execute("""
                INSERT INTO tasks VALUES (datetime('now'), 25.50)
            """)
            conn.commit()
            conn.close()
            
            # Should return summary
            summary = get_earnings(db_path)
            assert "total" in summary
            assert "daily" in summary
    
    def test_cli_ping(self):
        """Test CLI ping command."""
        result = subprocess.run(
            [sys.executable, "-m", "skills.mining.cli_dashboard", "--ping"],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), "../..")
        )
        
        output = result.stdout
        data = json.loads(output)
        assert data.get("status") == "ok"
        assert "timestamp" in data
    
    def test_cli_info(self):
        """Test CLI info command."""
        result = subprocess.run(
            [sys.executable, "-m", "skills.mining.cli_dashboard", "--info"],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), "../..")
        )
        
        output = result.stdout
        data = json.loads(output)
        assert data.get("name") == "openpango-mining-dashboard"
        assert data.get("version") == "1.0.0"
    
    def test_cli_list_tools(self):
        """Test CLI list-tools command."""
        result = subprocess.run(
            [sys.executable, "-m", "skills.mining.cli_dashboard", "--list-tools"],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), "../..")
        )
        
        output = result.stdout
        data = json.loads(output)
        assert "tools" in data
        assert len(data["tools"]) == 3
    
    def test_cli_list_resources(self):
        """Test CLI list-resources command."""
        result = subprocess.run(
            [sys.executable, "-m", "skills.mining.cli_dashboard", "--list-resources"],
            capture_output=True,
            text=True,
            cwd=os.path.join(os.path.dirname(__file__), "../..")
        )
        
        output = result.stdout
        data = json.loads(output)
        assert "resources" in data
    
    def test_textual_import_check(self):
        """Test that Textual import is checked."""
        try:
            from textual import __version__
            assert __version__ is not None
        except ImportError:
            pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
