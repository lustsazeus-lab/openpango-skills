#!/usr/bin/env python3
"""
mcp_client.py — OpenPango MCP Client.

Consume external MCP servers as OpenPango skills.
Enables agents to use tools exposed by any MCP-compatible server.
"""

import json
import subprocess
import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger("MCPClient")


class MCPClient:
    """Client for consuming MCP servers via stdio transport."""

    def __init__(self, command: str, args: List[str] = None, cwd: str = None):
        """
        Initialize an MCP client that communicates with an MCP server.

        Args:
            command: The command to start the MCP server (e.g., "python3")
            args: Arguments for the command (e.g., ["-m", "some_mcp_server"])
            cwd: Working directory for the server process
        """
        self.command = command
        self.args = args or []
        self.cwd = cwd
        self.process: Optional[subprocess.Popen] = None
        self.server_info: Optional[Dict] = None
        self._request_id = 0

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def connect(self) -> Dict:
        """Start the MCP server process and initialize the connection."""
        cmd = [self.command] + self.args
        self.process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.cwd,
            text=True,
        )

        # Send initialize request
        response = self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "openpango-client",
                "version": "1.0.0",
            },
        })

        self.server_info = response.get("result", {}).get("serverInfo")

        # Send initialized notification
        self._send_notification("notifications/initialized")

        logger.info(f"Connected to MCP server: {self.server_info}")
        return response.get("result", {})

    def _send_request(self, method: str, params: Dict = None) -> Dict:
        """Send a JSON-RPC request and wait for the response."""
        if not self.process or self.process.poll() is not None:
            raise RuntimeError("MCP server is not running")

        request = {
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": method,
        }
        if params:
            request["params"] = params

        self.process.stdin.write(json.dumps(request) + "\n")
        self.process.stdin.flush()

        response_line = self.process.stdout.readline()
        if not response_line:
            raise RuntimeError("MCP server closed connection")

        return json.loads(response_line)

    def _send_notification(self, method: str, params: Dict = None):
        """Send a JSON-RPC notification (no response expected)."""
        if not self.process or self.process.poll() is not None:
            return

        notification = {"jsonrpc": "2.0", "method": method}
        if params:
            notification["params"] = params

        self.process.stdin.write(json.dumps(notification) + "\n")
        self.process.stdin.flush()

    def list_tools(self) -> List[Dict]:
        """List available tools from the MCP server."""
        response = self._send_request("tools/list")
        return response.get("result", {}).get("tools", [])

    def call_tool(self, name: str, arguments: Dict = None) -> Dict:
        """Call a tool on the MCP server."""
        response = self._send_request("tools/call", {
            "name": name,
            "arguments": arguments or {},
        })
        result = response.get("result", {})
        if result.get("isError"):
            raise RuntimeError(f"Tool error: {result.get('content', [{}])[0].get('text', 'Unknown error')}")
        return result

    def list_resources(self) -> List[Dict]:
        """List available resources from the MCP server."""
        response = self._send_request("resources/list")
        return response.get("result", {}).get("resources", [])

    def disconnect(self):
        """Terminate the MCP server process."""
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)
            self.process = None
            logger.info("Disconnected from MCP server")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()
