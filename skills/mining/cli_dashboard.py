#!/usr/bin/env python3
"""
cli_dashboard.py - Rich Terminal UI Dashboard for OpenPango Mining Pool.

A Textual-based TUI that gives operators a live overview of their
OpenPango installation: active miners, running tasks, earnings, and health.

Keyboard shortcuts:
  q - Quit
  r - Refresh
  m - Miner detail
  t - Submit test task
"""

import os
import sqlite3
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any

try:
    from textual.app import App, ComposeResult
    from textual.containers import Container, Horizontal, Vertical
    from textual.widgets import Header, Footer, Static, DataTable, Label
    from textual.binding import Binding
    from textual.reactive import reactive
    from textual.screen import Screen
    from rich.text import Text
    from rich.style import Style
except ImportError:
    print("Error: textual not installed. Run: pip install textual")
    exit(1)

DB_PATH = os.getenv("MINING_POOL_DB", str(Path.home() / ".openclaw" / "mining_pool.db"))


def get_db_connection() -> sqlite3.Connection:
    """Get database connection."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


class MinerStatusPanel(Static):
    """Panel showing miner status."""
    
    def __init__(self):
        super().__init__()
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh miner data from database."""
        try:
            conn = get_db_connection()
            cursor = conn.execute("""
                SELECT miner_id, name, model, status, trust_score, 
                       total_tasks, successful_tasks, total_earned,
                       avg_response_ms, last_seen
                FROM miners
                ORDER BY last_seen DESC
                LIMIT 10
            """)
            miners = cursor.fetchall()
            conn.close()
            
            if not miners:
                self.update("[dim]No miners registered[/dim]")
                return
            
            lines = ["[bold cyan]📊 Miner Status[/bold cyan]\n"]
            for m in miners:
                status_color = {
                    'online': 'green',
                    'offline': 'red',
                    'busy': 'yellow'
                }.get(m['status'], 'white')
                
                success_rate = (m['successful_tasks'] / m['total_tasks'] * 100) if m['total_tasks'] > 0 else 0
                
                lines.append(
                    f"  [{status_color}]●[/{status_color}] {m['name'][:15]:<15} "
                    f"[dim]{m['model'][:12]}[/dim] "
                    f"Trust: {m['trust_score']:.0f} "
                    f"Tasks: {m['total_tasks']} "
                    f"Earned: ${m['total_earned']:.2f}"
                )
            
            self.update("\n".join(lines))
        except Exception as e:
            self.update(f"[red]Error: {e}[/red]")


class TaskQueuePanel(Static):
    """Panel showing task queue."""
    
    def __init__(self):
        super().__init__()
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh task data from database."""
        try:
            conn = get_db_connection()
            cursor = conn.execute("""
                SELECT task_id, miner_id, renter_id, model, status, 
                       cost, response_ms, created_at
                FROM task_log
                ORDER BY created_at DESC
                LIMIT 10
            """)
            tasks = cursor.fetchall()
            conn.close()
            
            if not tasks:
                self.update("[dim]No tasks yet[/dim]")
                return
            
            lines = ["[bold cyan]📋 Recent Tasks[/bold cyan]\n"]
            for t in tasks:
                status_color = {
                    'completed': 'green',
                    'pending': 'yellow',
                    'failed': 'red',
                    'running': 'blue'
                }.get(t['status'], 'white')
                
                created = datetime.fromisoformat(t['created_at'].replace('Z', '+00:00'))
                time_ago = datetime.now(timezone.utc) - created
                
                lines.append(
                    f"  [{status_color}]{t['status'][:8]:<8}[/{status_color}] "
                    f"{t['model'][:12] if t['model'] else 'unknown':<12} "
                    f"${t['cost']:.3f} "
                    f"[dim]{self._format_time_ago(time_ago)}[/dim]"
                )
            
            self.update("\n".join(lines))
        except Exception as e:
            self.update(f"[red]Error: {e}[/red]")
    
    def _format_time_ago(self, delta: timedelta) -> str:
        """Format time ago string."""
        if delta.seconds < 60:
            return f"{delta.seconds}s ago"
        elif delta.seconds < 3600:
            return f"{delta.seconds // 60}m ago"
        else:
            return f"{delta.seconds // 3600}h ago"


class EarningsPanel(Static):
    """Panel showing earnings graph."""
    
    def __init__(self):
        super().__init__()
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh earnings data from database."""
        try:
            conn = get_db_connection()
            
            # Total earnings
            cursor = conn.execute("SELECT SUM(total_earned) as total FROM miners")
            total = cursor.fetchone()['total'] or 0
            
            # Earnings by day (last 7 days)
            cursor = conn.execute("""
                SELECT DATE(created_at) as day, SUM(cost) as daily_earnings
                FROM task_log
                WHERE status = 'completed'
                  AND created_at >= DATE('now', '-7 days')
                GROUP BY day
                ORDER BY day
            """)
            daily = cursor.fetchall()
            
            # Task stats
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(cost) as total_cost
                FROM task_log
            """)
            stats = cursor.fetchone()
            conn.close()
            
            lines = ["[bold cyan]💰 Earnings[/bold cyan]\n"]
            lines.append(f"  Total Earned: [green]${total:.2f}[/green]")
            lines.append(f"  Total Tasks: {stats['total']}")
            lines.append(f"  Completed: [green]{stats['completed']}[/green]")
            lines.append(f"  Failed: [red]{stats['failed']}[/red]")
            
            # Simple bar chart
            if daily:
                lines.append("\n  [dim]Last 7 days:[/dim]")
                max_earnings = max(d['daily_earnings'] or 0 for d in daily) or 1
                for d in daily:
                    bar_len = int((d['daily_earnings'] or 0) / max_earnings * 10)
                    bar = "█" * bar_len
                    lines.append(f"    {d['day'][-5:]} {bar} ${d['daily_earnings']:.2f}")
            
            self.update("\n".join(lines))
        except Exception as e:
            self.update(f"[red]Error: {e}[/red]")


class SystemHealthPanel(Static):
    """Panel showing system health."""
    
    def __init__(self):
        super().__init__()
        self.refresh_data()
    
    def refresh_data(self):
        """Refresh system health data."""
        try:
            conn = get_db_connection()
            
            # Miner stats
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'online' THEN 1 ELSE 0 END) as online,
                    SUM(CASE WHEN status = 'busy' THEN 1 ELSE 0 END) as busy,
                    SUM(CASE WHEN status = 'offline' THEN 1 ELSE 0 END) as offline,
                    AVG(trust_score) as avg_trust
                FROM miners
            """)
            miner_stats = cursor.fetchone()
            
            # Pending tasks
            cursor = conn.execute("""
                SELECT COUNT(*) as pending
                FROM task_log
                WHERE status = 'pending'
            """)
            pending = cursor.fetchone()['pending']
            
            # Locked escrow
            cursor = conn.execute("""
                SELECT SUM(amount) as locked
                FROM escrow
                WHERE status = 'locked'
            """)
            escrow_locked = cursor.fetchone()['locked'] or 0
            conn.close()
            
            lines = ["[bold cyan]🏥 System Health[/bold cyan]\n"]
            
            # Miner status
            if miner_stats['total'] == 0:
                lines.append("  [dim]No miners registered[/dim]")
            else:
                lines.append(f"  Miners: {miner_stats['online']} [green]online[/green] / "
                           f"{miner_stats['busy']} [yellow]busy[/yellow] / "
                           f"{miner_stats['offline']} [red]offline[/red]")
                lines.append(f"  Avg Trust: {miner_stats['avg_trust']:.1f}")
            
            lines.append(f"  Pending Tasks: {pending}")
            lines.append(f"  Escrow Locked: ${escrow_locked:.2f}")
            
            # Overall health indicator
            if miner_stats['online'] > 0:
                lines.append("\n  [green]● System Healthy[/green]")
            elif miner_stats['total'] == 0:
                lines.append("\n  [yellow]● No Miners[/yellow]")
            else:
                lines.append("\n  [red]● All Miners Offline[/red]")
            
            self.update("\n".join(lines))
        except Exception as e:
            self.update(f"[red]Error: {e}[/red]")


class DashboardScreen(Screen):
    """Main dashboard screen."""
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("m", "miner_detail", "Miner Detail"),
        Binding("t", "test_task", "Test Task"),
    ]
    
    def compose(self) -> ComposeResult:
        """Compose the dashboard layout."""
        yield Header()
        yield Container(
            Horizontal(
                Vertical(
                    MinerStatusPanel(id="miner-status"),
                    SystemHealthPanel(id="system-health"),
                    classes="left-column"
                ),
                Vertical(
                    TaskQueuePanel(id="task-queue"),
                    EarningsPanel(id="earnings"),
                    classes="right-column"
                ),
                classes="main-content"
            )
        )
        yield Footer()
    
    def action_refresh(self):
        """Refresh all panels."""
        self.query_one(MinerStatusPanel).refresh_data()
        self.query_one(TaskQueuePanel).refresh_data()
        self.query_one(EarningsPanel).refresh_data()
        self.query_one(SystemHealthPanel).refresh_data()
    
    def action_miner_detail(self):
        """Show miner detail (placeholder)."""
        self.app.push_screen(MinerDetailScreen())
    
    def action_test_task(self):
        """Submit test task (placeholder)."""
        self.app.push_screen(TestTaskScreen())
    
    def action_quit(self):
        """Quit the application."""
        self.app.exit()


class MinerDetailScreen(Screen):
    """Screen showing miner details."""
    
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("q", "app.pop_screen", "Back"),
    ]
    
    def compose(self) -> ComposeResult:
        """Compose the screen."""
        yield Header()
        yield Static("[bold cyan]Miner Detail[/bold cyan]\n\n[dim]Press ESC or Q to go back[/dim]")
        yield Footer()


class TestTaskScreen(Screen):
    """Screen for submitting test tasks."""
    
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("q", "app.pop_screen", "Back"),
    ]
    
    def compose(self) -> ComposeResult:
        """Compose the screen."""
        yield Header()
        yield Static("[bold cyan]Submit Test Task[/bold cyan]\n\n[dim]Press ESC or Q to go back[/dim]")
        yield Footer()


class MiningDashboard(App):
    """OpenPango Mining Pool Dashboard."""
    
    CSS = """
    .main-content {
        layout: grid;
        grid-size: 2;
        grid-columns: 1fr 1fr;
    }
    
    .left-column, .right-column {
        height: 100%;
    }
    
    MinerStatusPanel, TaskQueuePanel, EarningsPanel, SystemHealthPanel {
        height: 50%;
        padding: 1;
        border: solid green;
    }
    """
    
    SCREENS = {
        "dashboard": DashboardScreen,
        "miner_detail": MinerDetailScreen,
        "test_task": TestTaskScreen,
    }
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
    ]
    
    def on_mount(self):
        """Initialize the app."""
        self.push_screen("dashboard")


if __name__ == "__main__":
    app = MiningDashboard()
    app.run()
