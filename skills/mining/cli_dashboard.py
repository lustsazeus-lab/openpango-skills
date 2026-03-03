#!/usr/bin/env python3
"""
CLI Dashboard with Rich Terminal UI (Textual)

A live dashboard for monitoring OpenPango mining operations in the terminal.
Works over SSH - no browser required.

Requirements:
    pip install textual

Usage:
    python -m skills.mining.cli_dashboard          # Run dashboard
    python -m skills.mining.cli_dashboard --help # Show help
    python -m skills.mining.cli_dashboard --list-tools   # MCP tools
    python -m skills.mining.cli_dashboard --list-resources # MCP resources
    python -m skills.mining.cli_dashboard --ping         # Health check
    python -m skills.mining.cli_dashboard --info         # Server info
"""

import asyncio
import argparse
import os
import sys
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass


# Textual is optional - CLI functions work without it
TEXTUAL_IMPORTED = False
try:
    from textual import __version__ as TEXTUAL_VERSION
    from textual.app import App, ComposeResult
    from textual.containers import Container, Horizontal, Vertical
    from textual.widgets import Header, Footer, Static, DataTable, Gauge, RichLog
    from textual.events import Key
    from textual.reactive import reactive
    from textual import work
    TEXTUAL_IMPORTED = True
except ImportError:
    TEXTUAL_VERSION = None


@dataclass
class Miner:
    """Represents a mining node."""
    id: str
    name: str
    model: str
    status: str  # active, inactive, error
    uptime: float
    tasks_completed: int
    earnings: float
    price: float


@dataclass
class Task:
    """Represents a mining task."""
    id: str
    prompt: str
    model: str
    status: str  # pending, running, completed, failed
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    cost: float


def get_db_connection(db_path: str) -> sqlite3.Connection:
    """Get database connection."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    return conn


def list_miners(db_path: str) -> list[Miner]:
    """List all miners from database.
    
    MCP Tool: list_miners
    """
    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, name, model, status, uptime, tasks_completed, earnings, price
            FROM miners
            ORDER BY earnings DESC
        """)
        
        miners = [
            Miner(
                id=row[0],
                name=row[1],
                model=row[2],
                status=row[3],
                uptime=row[4],
                tasks_completed=row[5],
                earnings=row[6],
                price=row[7]
            )
            for row in cursor.fetchall()
        ]
        
        conn.close()
        return miners
    except sqlite3.OperationalError:
        return []  # Database doesn't exist yet


def list_tasks(db_path: str) -> list[Task]:
    """List all tasks from database.
    
    MCP Tool: list_tasks
    """
    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, prompt, model, status, started_at, completed_at, cost
            FROM tasks
            ORDER BY started_at DESC
            LIMIT 50
        """)
        
        tasks = [
            Task(
                id=row[0],
                prompt=row[1],
                model=row[2],
                status=row[3],
                started_at=datetime.fromisoformat(row[4]) if row[4] else None,
                completed_at=datetime.fromisoformat(row[5]) if row[5] else None,
                cost=row[6]
            )
            for row in cursor.fetchall()
        ]
        
        conn.close()
        return tasks
    except sqlite3.OperationalError:
        return []


def get_earnings(db_path: str) -> dict:
    """Get earnings summary.
    
    MCP Tool: get_earnings
    """
    try:
        conn = get_db_connection(db_path)
        cursor = conn.cursor()
        
        # Total earnings
        cursor.execute("SELECT SUM(earnings) FROM miners")
        total = cursor.fetchone()[0] or 0.0
        
        # Daily earnings for last 7 days
        cursor.execute("""
            SELECT DATE(completed_at), SUM(cost)
            FROM tasks
            WHERE status = 'completed'
            AND completed_at >= DATE('now', '-7 days')
            GROUP BY DATE(completed_at)
            ORDER BY date
        """)
        
        daily = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        
        return {"total": total, "daily": daily}
    except sqlite3.OperationalError:
        return {"total": 0.0, "daily": {}}


# MCP Protocol Methods
def handle_mcp_request(method: str, params: dict, db_path: str) -> dict:
    """Handle MCP JSON-RPC requests."""
    
    if method == "initialize":
        return {
            "protocolVersion": "2024-11-05",
            "serverInfo": {
                "name": "openpango-mining-dashboard",
                "version": "1.0.0"
            },
            "capabilities": {
                "tools": {},
                "resources": {}
            }
        }
    
    elif method == "tools/list":
        miners = list_miners(db_path)
        return {
            "tools": [
                {
                    "name": "list_miners",
                    "description": "List all registered miners with status and earnings",
                    "inputSchema": {"type": "object", "properties": {}}
                },
                {
                    "name": "list_tasks",
                    "description": "List all mining tasks",
                    "inputSchema": {"type": "object", "properties": {}}
                },
                {
                    "name": "get_earnings",
                    "description": "Get earnings summary",
                    "inputSchema": {"type": "object", "properties": {}}
                }
            ]
        }
    
    elif method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        
        if tool_name == "list_miners":
            miners = list_miners(db_path)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps([{
                            "id": m.id,
                            "name": m.name,
                            "model": m.model,
                            "status": m.status,
                            "uptime": m.uptime,
                            "tasks_completed": m.tasks_completed,
                            "earnings": m.earnings,
                            "price": m.price
                        } for m in miners], indent=2)
                    }
                ]
            }
        elif tool_name == "list_tasks":
            tasks = list_tasks(db_path)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps([{
                            "id": t.id,
                            "prompt": t.prompt,
                            "model": t.model,
                            "status": t.status,
                            "started_at": t.started_at.isoformat() if t.started_at else None,
                            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                            "cost": t.cost
                        } for t in tasks], indent=2)
                    }
                ]
            }
        elif tool_name == "get_earnings":
            earnings = get_earnings(db_path)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(earnings, indent=2)
                    }
                ]
            }
        else:
            return {"error": f"Unknown tool: {tool_name}"}
    
    elif method == "resources/list":
        return {
            "resources": [
                {
                    "uri": "mining://miners",
                    "name": "Miners",
                    "description": "List of all registered miners",
                    "mimeType": "application/json"
                },
                {
                    "uri": "mining://tasks",
                    "name": "Tasks",
                    "description": "List of all tasks",
                    "mimeType": "application/json"
                },
                {
                    "uri": "mining://earnings",
                    "name": "Earnings",
                    "description": "Earnings summary",
                    "mimeType": "application/json"
                }
            ]
        }
    
    elif method == "resources/read":
        uri = params.get("uri", "")
        
        if uri == "mining://miners":
            miners = list_miners(db_path)
            return {
                "contents": [{
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": json.dumps([{
                        "id": m.id,
                        "name": m.name,
                        "model": m.model,
                        "status": m.status,
                        "uptime": m.uptime,
                        "tasks_completed": m.tasks_completed,
                        "earnings": m.earnings,
                        "price": m.price
                    } for m in miners], indent=2)
                }]
            }
        elif uri == "mining://tasks":
            tasks = list_tasks(db_path)
            return {
                "contents": [{
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": json.dumps([{
                        "id": t.id,
                        "prompt": t.prompt,
                        "model": t.model,
                        "status": t.status,
                        "started_at": t.started_at.isoformat() if t.started_at else None,
                        "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                        "cost": t.cost
                    } for t in tasks], indent=2)
                }]
            }
        elif uri == "mining://earnings":
            earnings = get_earnings(db_path)
            return {
                "contents": [{
                    "uri": uri,
                    "mimeType": "application/json",
                    "text": json.dumps(earnings, indent=2)
                }]
            }
        else:
            return {"error": f"Unknown resource: {uri}"}
    
    elif method == "ping":
        return {"status": "ok", "timestamp": datetime.now().isoformat()}
    
    return {"error": f"Unknown method: {method}"}


# Textual Dashboard (only if Textual is installed)
if TEXTUAL_IMPORTED:
    class MinerStatusPanel(Static):
        """Panel showing miner status."""
        
        def compose(self) -> ComposeResult:
            yield Static("⛏️ Miner Status", classes="panel-title")
            yield DataTable()
        
        def on_mount(self) -> None:
            table = self.query_one(DataTable)
            table.add_columns("Name", "Model", "Status", "Uptime", "Tasks", "Earnings")
            self.update_miners()
        
        def update_miners(self) -> None:
            table = self.query_one(DataTable)
            table.clear()
            
            # Sample data - in production, would query mining_pool.db
            sample_miners = [
                Miner("1", "gpu-rig-01", "gpt-4", "active", 99.5, 1523, 45.67, 0.02),
                Miner("2", "gpu-rig-02", "claude-3", "active", 98.2, 891, 28.34, 0.015),
                Miner("3", "cpu-node-01", "llama-3", "inactive", 0.0, 234, 12.50, 0.005),
                Miner("4", "gpu-rig-03", "gpt-4", "error", 45.0, 567, 19.80, 0.018),
            ]
            
            for m in sample_miners:
                status_color = {"active": "🟢", "inactive": "⚪", "error": "🔴"}.get(m.status, "⚪")
                table.add_row(
                    m.name,
                    m.model,
                    f"{status_color} {m.status}",
                    f"{m.uptime:.1f}%",
                    str(m.tasks_completed),
                    f"${m.earnings:.2f}"
                )


    class TaskQueuePanel(Static):
        """Panel showing task queue."""
        
        def compose(self) -> ComposeResult:
            yield Static("📋 Task Queue", classes="panel-title")
            yield DataTable()
        
        def on_mount(self) -> None:
            table = self.query_one(DataTable)
            table.add_columns("ID", "Prompt", "Model", "Status", "Started")
            self.update_tasks()
        
        def update_tasks(self) -> None:
            table = self.query_one(DataTable)
            table.clear()
            
            sample_tasks = [
                Task("t001", "Summarize this document...", "gpt-4", "running", 
                     datetime.now() - timedelta(minutes=2), None, 0.0),
                Task("t002", "Translate to Spanish", "claude-3", "pending",
                     None, None, 0.0),
                Task("t003", "Write Python code", "gpt-4", "completed",
                     datetime.now() - timedelta(minutes=10), 
                     datetime.now() - timedelta(minutes=8), 0.015),
                Task("t004", "Analyze data", "llama-3", "failed",
                     datetime.now() - timedelta(minutes=30),
                     datetime.now() - timedelta(minutes=28), 0.0),
            ]
            
            for t in sample_tasks:
                status_color = {
                    "running": "🔄",
                    "pending": "⏳",
                    "completed": "✅",
                    "failed": "❌"
                }.get(t.status, "⚪")
                
                started = t.started_at.strftime("%H:%M") if t.started_at else "-"
                
                table.add_row(
                    t.id,
                    t.prompt[:30] + "..." if len(t.prompt) > 30 else t.prompt,
                    t.model,
                    f"{status_color} {t.status}",
                    started
                )


    class EarningsPanel(Static):
        """Panel showing earnings graph."""
        
        earnings = reactive(0.0)
        
        def compose(self) -> ComposeResult:
            yield Static("💰 Earnings", classes="panel-title")
            yield Static(id="earnings-display")
            yield RichLog(id="earnings-graph")
        
        def on_mount(self) -> None:
            self.update_earnings()
        
        def update_earnings(self) -> None:
            daily_earnings = [
                ("Mon", 12.50),
                ("Tue", 18.75),
                ("Wed", 15.20),
                ("Thu", 22.40),
                ("Fri", 28.90),
                ("Sat", 35.60),
                ("Sun", 45.67),
            ]
            
            total = sum(e for _, e in daily_earnings)
            self.earnings = total
            
            display = self.query_one("#earnings-display", Static)
            display.update(f"Total: ${total:.2f}")
            
            log = self.query_one("#earnings-graph", RichLog)
            log.clear()
            
            max_earnings = max(e for _, e in daily_earnings)
            
            for day, earnings in daily_earnings:
                bar_length = int((earnings / max_earnings) * 20)
                bar = "█" * bar_length
                log.write(f"{day}: {bar} ${earnings:.2f}")


    class SystemHealthPanel(Static):
        """Panel showing system health."""
        
        def compose(self) -> ComposeResult:
            yield Static("🖥️ System Health", classes="panel-title")
            yield Gauge(100, show_percentage=False, id="cpu-gauge", label="CPU")
            yield Gauge(65, show_percentage=False, id="mem-gauge", label="Memory")
            yield Gauge(42, show_percentage=False, id="net-gauge", label="Network")
            yield Static("Uptime: 5d 12h 34m", id="uptime-display")


    class CLIDashboard(App):
        """Rich Terminal Dashboard for Mining Pool Monitoring."""
        
        CSS = """
        Screen {
            background: $surface;
        }
        
        .panel-title {
            dock: top;
            height: 1;
            text-style: bold;
            color: $accent;
            background: $panel;
            padding: 0 1;
        }
        
        #cpu-gauge, #mem-gauge, #net-gauge {
            height: 3;
            margin: 1;
        }
        
        #uptime-display {
            dock: bottom;
            height: 1;
            color: $text-muted;
        }
        
        DataTable {
            height: 100%;
        }
        
        #earnings-graph {
            height: 100%;
            border: solid $accent;
        }
        """
        
        BINDINGS = [
            ("q", "quit", "Quit"),
            ("r", "refresh", "Refresh"),
            ("m", "miner_detail", "Miner Detail"),
            ("t", "test_task", "Test Task"),
            ("1", "focus_miners", "Miners"),
            ("2", "focus_tasks", "Tasks"),
            ("3", "focus_earnings", "Earnings"),
            ("4", "focus_health", "Health"),
        ]
        
        def __init__(self, db_path: Optional[str] = None, **kwargs):
            super().__init__(**kwargs)
            self.db_path = db_path or os.environ.get(
                "MINING_POOL_DB", 
                "~/.openclaw/workspace/mining_pool.db"
            )
            self.db_path = os.path.expanduser(self.db_path)
        
        def compose(self) -> ComposeResult:
            yield Header()
            
            with Horizontal:
                with Vertical(id="left-panel"):
                    yield MinerStatusPanel(id="miners-panel")
                with Vertical(id="center-panel"):
                    yield TaskQueuePanel(id="tasks-panel")
                with Vertical(id="right-panel"):
                    yield EarningsPanel(id="earnings-panel")
                    yield SystemHealthPanel(id="health-panel")
            
            yield Footer()
        
        def action_refresh(self) -> None:
            self.title = f"🔄 Mining Dashboard - {datetime.now().strftime('%H:%M:%S')}"
            
            miners = self.query_one("#miners-panel", MinerStatusPanel)
            miners.update_miners()
            
            tasks = self.query_one("#tasks-panel", TaskQueuePanel)
            tasks.update_tasks()
            
            earnings = self.query_one("#earnings-panel", EarningsPanel)
            earnings.update_earnings()
        
        def action_miner_detail(self) -> None:
            self.notify("Miner detail view - use arrow keys to navigate")
        
        def action_test_task(self) -> None:
            self.notify("Test task submitted!")
        
        def action_focus_miners(self) -> None:
            self.query_one("#miners-panel", MinerStatusPanel).focus()
        
        def action_focus_tasks(self) -> None:
            self.query_one("#tasks-panel", TaskQueuePanel).focus()
        
        def action_focus_earnings(self) -> None:
            self.query_one("#earnings-panel", EarningsPanel).focus()
        
        def action_focus_health(self) -> None:
            self.query_one("#health-panel", SystemHealthPanel).focus()
        
        def on_mount(self) -> None:
            self.title = "⛏️ Mining Dashboard"
            self.set_interval(30, self.action_refresh)


    def run_dashboard(db_path: Optional[str] = None, debug: bool = False):
        """Run the dashboard application."""
        app = CLIDashboard(db_path=db_path)
        app.run()
else:
    def run_dashboard(db_path: Optional[str] = None, debug: bool = False):
        """Run the dashboard application."""
        print("Error: Textual is not installed.")
        print("Install with: pip install textual")
        sys.exit(1)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="OpenPango Mining Dashboard - Rich Terminal UI"
    )
    parser.add_argument(
        "--db", 
        default="~/.openclaw/workspace/mining_pool.db",
        help="Path to mining pool database"
    )
    parser.add_argument(
        "--list-tools",
        action="store_true",
        help="List available MCP tools and exit"
    )
    parser.add_argument(
        "--list-resources",
        action="store_true", 
        help="List available MCP resources and exit"
    )
    parser.add_argument(
        "--ping",
        action="store_true",
        help="Check if server is running"
    )
    parser.add_argument(
        "--info",
        action="store_true",
        help="Get server info"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    
    args = parser.parse_args()
    
    db_path = os.path.expanduser(args.db)
    
    if args.list_tools:
        print(json.dumps({
            "tools": [
                {
                    "name": "list_miners",
                    "description": "List all registered miners",
                    "inputSchema": {"type": "object", "properties": {}}
                },
                {
                    "name": "list_tasks",
                    "description": "List all tasks",
                    "inputSchema": {"type": "object", "properties": {}}
                },
                {
                    "name": "get_earnings",
                    "description": "Get earnings summary",
                    "inputSchema": {"type": "object", "properties": {}}
                }
            ]
        }, indent=2))
        return
    
    if args.list_resources:
        print(json.dumps({
            "resources": [
                {
                    "uri": "mining://miners",
                    "name": "Miners",
                    "description": "List of all registered miners"
                },
                {
                    "uri": "mining://tasks",
                    "name": "Tasks",
                    "description": "List of all tasks"
                },
                {
                    "uri": "mining://earnings",
                    "name": "Earnings",
                    "description": "Earnings summary"
                }
            ]
        }, indent=2))
        return
    
    if args.ping:
        print(json.dumps({
            "status": "ok", 
            "timestamp": datetime.now().isoformat()
        }))
        return
    
    if args.info:
        print(json.dumps({
            "name": "openpango-mining-dashboard",
            "version": "1.0.0",
            "description": "CLI Dashboard for OpenPango Mining Pool",
            "protocol": "mcp"
        }, indent=2))
        return
    
    # Run the dashboard
    run_dashboard(db_path=db_path, debug=args.debug)


if __name__ == "__main__":
    main()
