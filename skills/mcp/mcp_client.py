#!/usr/bin/env python3
"""
mcp_client.py - MCP (Model Context Protocol) Client for OpenPango Skills.
Consumes external MCP servers as OpenPango skills.
"""
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass

BASE_DIR = Path(__file__).parent.parent


@dataclass
class MCPTool:
    """MCP Tool definition."""
    name: str
    description: str
    input_schema: dict


@dataclass  
class MCPResource:
    """MCP Resource definition."""
    uri: str
    name: str
    description: str
    mime_type: str


class MCPClient:
    """MCP Client that connects to external MCP servers."""
    
    def __init__(self, command: list, env: Optional[dict] = None):
        self.command = command
        self.env = env or {}
        self.process: Optional[subprocess.Popen] = None
        self.request_id = 0
        self.capabilities = {}
        self.server_info = {}
    
    def start(self):
        """Start the MCP server process."""
        full_env = {**subprocess.os.environ.copy(), **self.env}
        
        self.process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=full_env,
            text=True,
            bufsize=1
        )
        
        # Initialize connection
        response = self.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "clientInfo": {
                "name": "openpango-mcp-client",
                "version": "1.0.0"
            }
        })
        
        if response and "result" in response:
            self.capabilities = response["result"].get("capabilities", {})
            self.server_info = response["result"].get("serverInfo", {})
    
    def stop(self):
        """Stop the MCP server process."""
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)
    
    def send_request(self, method: str, params: dict = None) -> Optional[dict]:
        """Send a JSON-RPC request to the MCP server."""
        if not self.process or self.process.poll() is not None:
            return None
        
        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method,
            "params": params or {}
        }
        self.request_id += 1
        
        try:
            self.process.stdin.write(json.dumps(request) + "\n")
            self.process.stdin.flush()
            
            # Read response
            line = self.process.stdout.readline()
            if line:
                return json.loads(line)
        except Exception as e:
            print(f"Error sending request: {e}", file=sys.stderr)
        
        return None
    
    def list_tools(self) -> list[MCPTool]:
        """List available tools from the MCP server."""
        response = self.send_request("tools/list")
        
        if response and "result" in response:
            tools = []
            for t in response["result"].get("tools", []):
                tools.append(MCPTool(
                    name=t["name"],
                    description=t.get("description", ""),
                    input_schema=t.get("inputSchema", {})
                ))
            return tools
        return []
    
    def call_tool(self, name: str, arguments: dict = None) -> Any:
        """Call a tool on the MCP server."""
        response = self.send_request("tools/call", {
            "name": name,
            "arguments": arguments or {}
        })
        
        if response and "result" in response:
            return response["result"]
        return None
    
    def list_resources(self) -> list[MCPResource]:
        """List available resources from the MCP server."""
        response = self.send_request("resources/list")
        
        if response and "result" in response:
            resources = []
            for r in response["result"].get("resources", []):
                resources.append(MCPResource(
                    uri=r["uri"],
                    name=r.get("name", ""),
                    description=r.get("description", ""),
                    mime_type=r.get("mimeType", "text/plain")
                ))
            return resources
        return []
    
    def read_resource(self, uri: str) -> Optional[str]:
        """Read a resource from the MCP server."""
        response = self.send_request("resources/read", {"uri": uri})
        
        if response and "result" in response:
            contents = response["result"].get("contents", [])
            if contents:
                return contents[0].get("text")
        return None


class MCPClientPool:
    """Pool of MCP clients for managing multiple server connections."""
    
    def __init__(self):
        self.clients: dict[str, MCPClient] = {}
    
    def add_server(self, name: str, command: list, env: Optional[dict] = None):
        """Add an MCP server to the pool."""
        client = MCPClient(command, env)
        client.start()
        self.clients[name] = client
    
    def remove_server(self, name: str):
        """Remove an MCP server from the pool."""
        if name in self.clients:
            self.clients[name].stop()
            del self.clients[name]
    
    def get_client(self, name: str) -> Optional[MCPClient]:
        """Get an MCP client by name."""
        return self.clients.get(name)
    
    def list_all_tools(self) -> dict[str, list[MCPTool]]:
        """List tools from all servers."""
        result = {}
        for name, client in self.clients.items():
            result[name] = client.list_tools()
        return result
    
    def close_all(self):
        """Close all MCP server connections."""
        for client in self.clients.values():
            client.stop()
        self.clients.clear()


def load_mcp_servers(config_path: Optional[Path] = None) -> MCPClientPool:
    """Load MCP servers from configuration."""
    if config_path is None:
        config_path = BASE_DIR / "mcp_config.json"
    
    pool = MCPClientPool()
    
    if not config_path.exists():
        return pool
    
    with open(config_path) as f:
        config = json.load(f)
    
    servers = config.get("mcp_servers", {})
    
    for name, server_config in servers.items():
        command = server_config.get("command", [])
        env = server_config.get("env", {})
        
        if command:
            pool.add_server(name, command, env)
    
    return pool


def main():
    """Test MCP client functionality."""
    import argparse
    
    parser = argparse.ArgumentParser(description="OpenPango MCP Client")
    parser.add_argument("--server", required=True, help="MCP server command")
    parser.add_argument("--list-tools", action="store_true", help="List available tools")
    parser.add_argument("--call", help="Tool name to call")
    parser.add_argument("--args", help="JSON arguments for tool call")
    args = parser.parse_args()
    
    command = args.server.split()
    pool = MCPClientPool()
    
    try:
        pool.add_server("test", command)
        
        if args.list_tools:
            tools = pool.list_all_tools()
            print("Available tools:")
            for server, tool_list in tools.items():
                print(f"\n{server}:")
                for tool in tool_list:
                    print(f"  - {tool.name}: {tool.description}")
        
        if args.call:
            tool_args = json.loads(args.args) if args.args else {}
            result = pool.clients["test"].call_tool(args.call, tool_args)
            print(json.dumps(result, indent=2))
    finally:
        pool.close_all()


if __name__ == "__main__":
    main()
