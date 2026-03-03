#!/usr/bin/env python3
"""
MCP Client - Consume external MCP servers as OpenPango skills.

This module implements an MCP client that can connect to external MCP servers
and expose their tools as OpenPango skills.
"""

import json
import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import urllib.request
import urllib.error
import urllib.parse

JSONRPC_VERSION = "2.0"

DEFAULT_TIMEOUT = 30


@dataclass
class MCPToolDefinition:
    """Definition of an MCP tool from a server."""
    name: str
    description: str
    input_schema: Dict[str, Any]


@dataclass
class MCPResource:
    """Definition of an MCP resource."""
    uri: str
    name: str
    description: str
    mime_type: str


class MCPClient:
    """MCP Client for connecting to external MCP servers."""
    
    def __init__(self, server_url: str, auth_token: Optional[str] = None, timeout: int = DEFAULT_TIMEOUT):
        self.server_url = server_url.rstrip('/')
        self.auth_token = auth_token
        self.timeout = timeout
        self._initialized = False
        self._server_info: Dict[str, Any] = {}
        self._tools: Dict[str, MCPToolDefinition] = {}
        self._resources: Dict[str, MCPResource] = {}
    
    def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Send a JSON-RPC request to the MCP server."""
        request = {
            "jsonrpc": JSONRPC_VERSION,
            "id": 1,
            "method": method
        }
        if params:
            request["params"] = params
        
        data = json.dumps(request).encode('utf-8')
        
        req = urllib.request.Request(
            f"{self.server_url}/mcp",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        )
        
        if self.auth_token:
            req.add_header("Authorization", f"Bearer {self.auth_token}")
        
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.URLError as e:
            raise ConnectionError(f"Failed to connect to MCP server: {e}")
        except urllib.error.HTTPError as e:
            raise ConnectionError(f"MCP server error: {e.code} {e.reason}")
    
    def _send_notification(self, method: str, params: Optional[Dict[str, Any]] = None):
        """Send a notification (no response expected)."""
        request = {
            "jsonrpc": JSONRPC_VERSION,
            "method": method
        }
        if params:
            request["params"] = params
        
        data = json.dumps(request).encode('utf-8')
        
        req = urllib.request.Request(
            f"{self.server_url}/mcp",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        )
        
        if self.auth_token:
            req.add_header("Authorization", f"Bearer {self.auth_token}")
        
        try:
            urllib.request.urlopen(req, timeout=5)
        except:
            pass  # Notifications don't expect responses
    
    def initialize(self) -> Dict[str, Any]:
        """Initialize connection to MCP server."""
        if self._initialized:
            return self._server_info
        
        result = self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "clientInfo": {
                "name": "openpango-mcp-client",
                "version": "1.0.0"
            }
        })
        
        if "error" in result:
            raise ConnectionError(f"Initialization failed: {result['error']}")
        
        self._server_info = result.get("result", {})
        self._initialized = True
        
        # Load tools and resources
        self.list_tools()
        self.list_resources()
        
        return self._server_info
    
    def ping(self) -> bool:
        """Ping the MCP server."""
        try:
            result = self._send_request("ping")
            return result.get("result", {}).get("pong", False)
        except:
            return False
    
    def list_tools(self) -> List[MCPToolDefinition]:
        """List available tools from the MCP server."""
        if not self._initialized:
            self.initialize()
        
        result = self._send_request("tools/list")
        
        if "error" in result:
            raise ConnectionError(f"Failed to list tools: {result['error']}")
        
        tools = []
        for tool_data in result.get("result", {}).get("tools", []):
            tools.append(MCPToolDefinition(
                name=tool_data.get("name", ""),
                description=tool_data.get("description", ""),
                input_schema=tool_data.get("inputSchema", {})
            ))
            self._tools[tool_data.get("name", "")] = tools[-1]
        
        return tools
    
    def call_tool(self, tool_name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        """Call a tool on the MCP server."""
        if not self._initialized:
            self.initialize()
        
        result = self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments or {}
        })
        
        if "error" in result:
            raise ConnectionError(f"Tool call failed: {result['error']}")
        
        return result.get("result", {})
    
    def list_resources(self) -> List[MCPResource]:
        """List available resources from the MCP server."""
        if not self._initialized:
            self.initialize()
        
        result = self._send_request("resources/list")
        
        if "error" in result:
            raise ConnectionError(f"Failed to list resources: {result['error']}")
        
        resources = []
        for resource_data in result.get("result", {}).get("resources", []):
            resources.append(MCPResource(
                uri=resource_data.get("uri", ""),
                name=resource_data.get("name", ""),
                description=resource_data.get("description", ""),
                mime_type=resource_data.get("mimeType", "application/json")
            ))
            self._resources[resource_data.get("uri", "")] = resources[-1]
        
        return resources
    
    def read_resource(self, uri: str) -> Any:
        """Read a resource from the MCP server."""
        if not self._initialized:
            self.initialize()
        
        result = self._send_request("resources/read", {
            "uri": uri
        })
        
        if "error" in result:
            raise ConnectionError(f"Resource read failed: {result['error']}")
        
        contents = result.get("result", {}).get("contents", [])
        if contents:
            # Return the first content's data
            content = contents[0]
            if "text" in content:
                try:
                    return json.loads(content["text"])
                except:
                    return content["text"]
            if "blob" in content:
                import base64
                return base64.b64decode(content["blob"])
        
        return None
    
    def get_server_info(self) -> Dict[str, Any]:
        """Get server information."""
        if not self._initialized:
            self.initialize()
        return self._server_info
    
    @property
    def tools(self) -> Dict[str, MCPToolDefinition]:
        """Get cached tools."""
        return self._tools
    
    @property
    def resources(self) -> Dict[str, MCPResource]:
        """Get cached resources."""
        return self._resources


class MCPClientRegistry:
    """Registry for managing multiple MCP client connections."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.clients: Dict[str, MCPClient] = {}
        self.config = self._load_config(config_path)
        self._load_clients()
    
    def _load_config(self, config_path: Optional[Path]) -> Dict[str, Any]:
        """Load MCP client configuration."""
        default_config = Path.home() / ".openclaw" / "workspace" / "mcp_servers.json"
        path = config_path or default_config
        
        if path.exists():
            with open(path) as f:
                return json.load(f)
        
        return {"servers": {}}
    
    def _load_clients(self):
        """Load configured MCP clients."""
        servers = self.config.get("servers", {})
        for name, server_config in servers.items():
            try:
                client = MCPClient(
                    server_url=server_config.get("url", ""),
                    auth_token=server_config.get("auth_token"),
                    timeout=server_config.get("timeout", DEFAULT_TIMEOUT)
                )
                self.clients[name] = client
            except Exception as e:
                print(f"Warning: Failed to load MCP server '{name}': {e}")
    
    def add_server(self, name: str, url: str, auth_token: Optional[str] = None):
        """Add a new MCP server to the registry."""
        self.clients[name] = MCPClient(url, auth_token)
    
    def remove_server(self, name: str):
        """Remove an MCP server from the registry."""
        if name in self.clients:
            del self.clients[name]
    
    def get_client(self, name: str) -> Optional[MCPClient]:
        """Get an MCP client by name."""
        return self.clients.get(name)
    
    def list_servers(self) -> List[str]:
        """List all registered server names."""
        return list(self.clients.keys())
    
    def initialize_all(self) -> Dict[str, Any]:
        """Initialize all MCP clients."""
        results = {}
        for name, client in self.clients.items():
            try:
                results[name] = client.initialize()
            except Exception as e:
                results[name] = {"error": str(e)}
        return results


def main():
    """Main entry point for MCP client CLI."""
    parser = argparse.ArgumentParser(description="MCP Client for OpenPango")
    parser.add_argument("server_url", help="URL of the MCP server")
    parser.add_argument("--auth-token", help="Authentication token")
    parser.add_argument("--list-tools", action="store_true", help="List available tools")
    parser.add_argument("--list-resources", action="store_true", help="List available resources")
    parser.add_argument("--call", dest="tool_name", help="Tool to call")
    parser.add_argument("--args", help="JSON arguments for tool call")
    parser.add_argument("--read", dest="resource_uri", help="Resource URI to read")
    parser.add_argument("--ping", action="store_true", help="Ping the server")
    parser.add_argument("--info", action="store_true", help="Get server info")
    
    args = parser.parse_args()
    
    client = MCPClient(args.server_url, args.auth_token)
    
    if args.list_tools:
        tools = client.list_tools()
        print(f"Available Tools ({len(tools)}):")
        for tool in tools:
            print(f"  - {tool.name}")
            print(f"    {tool.description}")
            print()
    
    if args.list_resources:
        resources = client.list_resources()
        print(f"Available Resources ({len(resources)}):")
        for resource in resources:
            print(f"  - {resource.name} ({resource.uri})")
            print(f"    {resource.description}")
            print()
    
    if args.ping:
        if client.ping():
            print("Server is alive")
        else:
            print("Server not responding")
            sys.exit(1)
    
    if args.info:
        info = client.initialize()
        print(json.dumps(info, indent=2))
    
    if args.tool_name:
        tool_args = {}
        if args.args:
            try:
                tool_args = json.loads(args.args)
            except json.JSONDecodeError:
                print("Error: Invalid JSON in --args")
                sys.exit(1)
        
        result = client.call_tool(args.tool_name, tool_args)
        print(json.dumps(result, indent=2))
    
    if args.resource_uri:
        result = client.read_resource(args.resource_uri)
        if isinstance(result, dict):
            print(json.dumps(result, indent=2))
        else:
            print(result)


if __name__ == "__main__":
    main()
