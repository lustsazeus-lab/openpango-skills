#!/usr/bin/env python3
"""
MCP Server - Expose OpenPango skills as MCP tools.

This module implements an MCP (Model Context Protocol) server that exposes
OpenPango skills as MCP-compatible tools, enabling integration with MCP
clients like Claude Desktop, Cursor, Windsurf, etc.
"""

import json
import os
import sys
import subprocess
import argparse
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import threading
import http.server
import socketserver
import urllib.parse

# MCP Protocol constants
MCP_VERSION = "2024-11-05"
JSONRPC_VERSION = "2.0"

SKILLS_DIR = Path(__file__).parent.parent
CONFIG_FILE = Path.home() / ".openclaw" / "workspace" / "mcp_config.json"


@dataclass
class MCPTool:
    """Represents an MCP tool."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable = field(default=None)


@dataclass
class MCPResource:
    """Represents an MCP resource."""
    uri: str
    name: str
    description: str
    mime_type: str = "application/json"


class MCPError(Exception):
    """MCP protocol error."""
    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)


# Error codes
ERROR_PARSE_ERROR = -32700
ERROR_INVALID_REQUEST = -32600
ERROR_METHOD_NOT_FOUND = -32601
ERROR_INVALID_PARAMS = -32602
ERROR_INTERNAL_ERROR = -32603


class MCPServer:
    """MCP Server implementation."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config = self._load_config(config_path)
        self.tools: Dict[str, MCPTool] = {}
        self.resources: Dict[str, MCPResource] = {}
        self._discover_skills()
    
    def _load_config(self, config_path: Optional[Path]) -> Dict[str, Any]:
        """Load MCP configuration."""
        path = config_path or CONFIG_FILE
        if path.exists():
            with open(path) as f:
                return json.load(f)
        return {
            "allowlist": [],  # Empty means all skills allowed
            "auth_tokens": {},
            "port": 8765
        }
    
    def _discover_skills(self):
        """Auto-discover installed OpenPango skills."""
        if not SKILLS_DIR.exists():
            return
        
        for skill_dir in SKILLS_DIR.iterdir():
            if not skill_dir.is_dir():
                continue
            if skill_dir.name.startswith('.'):
                continue
            
            # Check if skill is in allowlist
            if self.config.get("allowlist") and skill_dir.name not in self.config["allowlist"]:
                continue
            
            # Look for skill entry point
            skill_files = list(skill_dir.glob("*.py"))
            py_files = [f for f in skill_files if f.name not in ["__pycache__", "test_*.py", "*_test.py"]]
            
            if py_files:
                # Read SKILL.md for description
                skill_md = skill_dir / "SKILL.md"
                description = f"OpenPango skill: {skill_dir.name}"
                if skill_md.exists():
                    try:
                        content = skill_md.read_text()
                        # Extract first paragraph
                        lines = content.split('\n')
                        in_frontmatter = False
                        for line in lines:
                            if line.strip() == '---':
                                in_frontmatter = not in_frontmatter
                                continue
                            if not in_frontmatter and line.strip():
                                description = line.strip()
                                break
                    except:
                        pass
                
                # Create tool for this skill
                tool_name = f"skill_{skill_dir.name}"
                self.tools[tool_name] = MCPTool(
                    name=tool_name,
                    description=description,
                    input_schema={
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "enum": ["list", "info", "execute"],
                                "description": "Action to perform on the skill"
                            },
                            "skill_name": {
                                "type": "string",
                                "description": f"Name of the skill ({skill_dir.name})"
                            },
                            "params": {
                                "type": "object",
                                "description": "Parameters for skill execution"
                            }
                        },
                        "required": ["action"]
                    },
                    handler=self._create_skill_handler(skill_dir.name)
                )
                
                # Add skill info as resource
                resource_uri = f"skill://{skill_dir.name}/info"
                self.resources[resource_uri] = MCPResource(
                    uri=resource_uri,
                    name=f"{skill_dir.name}_info",
                    description=description,
                    mime_type="application/json"
                )
    
    def _create_skill_handler(self, skill_name: str) -> Callable:
        """Create a handler function for a specific skill."""
        def handler(params: Dict[str, Any]) -> Dict[str, Any]:
            action = params.get("action", "info")
            
            if action == "list":
                return {
                    "skill": skill_name,
                    "available": True,
                    "actions": ["info", "execute"]
                }
            elif action == "info":
                skill_dir = SKILLS_DIR / skill_name
                return {
                    "skill": skill_name,
                    "path": str(skill_dir),
                    "exists": skill_dir.exists()
                }
            elif action == "execute":
                skill_params = params.get("params", {})
                return self._execute_skill(skill_name, skill_params)
            else:
                raise MCPError(ERROR_INVALID_PARAMS, f"Unknown action: {action}")
        
        return handler
    
    def _execute_skill(self, skill_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a skill with given parameters."""
        skill_dir = SKILLS_DIR / skill_name
        if not skill_dir.exists():
            raise MCPError(ERROR_INVALID_PARAMS, f"Skill not found: {skill_name}")
        
        # Find main Python file
        py_files = list(skill_dir.glob("*.py"))
        main_file = None
        for f in py_files:
            if f.name not in ["__pycache__", "test_*.py", "*_test.py"]:
                main_file = f
                break
        
        if not main_file:
            raise MCPError(ERROR_INVALID_PARAMS, f"No executable found in skill: {skill_name}")
        
        # Try to execute the skill
        try:
            # Pass params as JSON
            param_json = json.dumps(params)
            result = subprocess.run(
                ["python3", str(main_file), "--json-input", param_json],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(skill_dir)
            )
            
            if result.returncode == 0:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    return {"output": result.stdout}
            else:
                return {"error": result.stderr, "returncode": result.returncode}
        except subprocess.TimeoutExpired:
            raise MCPError(ERROR_INTERNAL_ERROR, "Skill execution timed out")
        except Exception as e:
            raise MCPError(ERROR_INTERNAL_ERROR, str(e))
    
    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an MCP JSON-RPC request."""
        method = request.get("method")
        request_id = request.get("id")
        params = request.get("params", {})
        
        try:
            if method == "tools/list":
                result = self._handle_tools_list()
            elif method == "tools/call":
                result = self._handle_tools_call(params)
            elif method == "resources/list":
                result = self._handle_resources_list()
            elif method == "resources/read":
                result = self._handle_resources_read(params)
            elif method == "initialize":
                result = self._handle_initialize(params)
            elif method == "ping":
                result = {"pong": True}
            else:
                raise MCPError(ERROR_METHOD_NOT_FOUND, f"Unknown method: {method}")
            
            return {
                "jsonrpc": JSONRPC_VERSION,
                "id": request_id,
                "result": result
            }
        except MCPError as e:
            return {
                "jsonrpc": JSONRPC_VERSION,
                "id": request_id,
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "data": e.data
                }
            }
        except Exception as e:
            return {
                "jsonrpc": JSONRPC_VERSION,
                "id": request_id,
                "error": {
                    "code": ERROR_INTERNAL_ERROR,
                    "message": str(e)
                }
            }
    
    def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request."""
        return {
            "protocolVersion": MCP_VERSION,
            "serverInfo": {
                "name": "openpango-mcp-server",
                "version": "1.0.0"
            },
            "capabilities": {
                "tools": {},
                "resources": {}
            }
        }
    
    def _handle_tools_list(self) -> Dict[str, Any]:
        """Handle tools/list request."""
        tools = []
        for tool in self.tools.values():
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.input_schema
            })
        return {"tools": tools}
    
    def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tools/call request."""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name not in self.tools:
            raise MCPError(ERROR_METHOD_NOT_FOUND, f"Tool not found: {tool_name}")
        
        tool = self.tools[tool_name]
        
        if tool.handler:
            result = tool.handler(arguments)
        else:
            result = {"status": "no handler implemented"}
        
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result)
                }
            ]
        }
    
    def _handle_resources_list(self) -> Dict[str, Any]:
        """Handle resources/list request."""
        resources = []
        for resource in self.resources.values():
            resources.append({
                "uri": resource.uri,
                "name": resource.name,
                "description": resource.description,
                "mimeType": resource.mime_type
            })
        return {"resources": resources}
    
    def _handle_resources_read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resources/read request."""
        uri = params.get("uri")
        
        if uri not in self.resources:
            raise MCPError(ERROR_METHOD_NOT_FOUND, f"Resource not found: {uri}")
        
        resource = self.resources[uri]
        
        # Parse skill info from URI
        if uri.startswith("skill://"):
            parts = uri.replace("skill://", "").split("/")
            skill_name = parts[0]
            
            if parts[1] == "info":
                return {
                    "contents": [
                        {
                            "uri": uri,
                            "mimeType": resource.mime_type,
                            "text": json.dumps(self._get_skill_info(skill_name))
                        }
                    ]
                }
        
        raise MCPError(ERROR_INVALID_PARAMS, f"Cannot read resource: {uri}")
    
    def _get_skill_info(self, skill_name: str) -> Dict[str, Any]:
        """Get information about a skill."""
        skill_dir = SKILLS_DIR / skill_name
        
        info = {
            "name": skill_name,
            "exists": skill_dir.exists()
        }
        
        if skill_dir.exists():
            info["path"] = str(skill_dir)
            
            # Read SKILL.md
            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                info["has_docs"] = True
            
            # List Python files
            py_files = list(skill_dir.glob("*.py"))
            info["files"] = [f.name for f in py_files if not f.name.startswith("__")]
        
        return info


class MCPRequestHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for MCP server."""
    
    server: MCPServer
    
    def do_POST(self):
        """Handle POST requests."""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            request = json.loads(body)
        except json.JSONDecodeError:
            self.send_error_response({
                "jsonrpc": JSONRPC_VERSION,
                "error": {
                    "code": ERROR_PARSE_ERROR,
                    "message": "Invalid JSON"
                }
            })
            return
        
        # Check auth token
        auth_header = self.headers.get('Authorization', '')
        if auth_header:
            token = auth_header.replace('Bearer ', '')
            if token != self.server.config.get("auth_tokens", {}).get("default", ""):
                self.send_error_response({
                    "jsonrpc": JSONRPC_VERSION,
                    "error": {
                        "code": ERROR_INVALID_REQUEST,
                        "message": "Unauthorized"
                    }
                })
                return
        
        response = self.server.handle_request(request)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def send_error_response(self, response: Dict[str, Any]):
        """Send error response."""
        self.send_response(400)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def log_message(self, format, *args):
        """Suppress HTTP logging."""
        pass


def run_server(port: int = 8765):
    """Run the MCP server."""
    server = MCPServer()
    
    with socketserver.TCPServer(("", port), MCPRequestHandler) as httpd:
        httpd.server = server
        print(f"MCP Server running on port {port}")
        print(f"Discovered {len(server.tools)} tools and {len(server.resources)} resources")
        httpd.serve_forever()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="MCP Server for OpenPango Skills")
    parser.add_argument("--port", type=int, default=8765, help="Port to run server on")
    parser.add_argument("--config", type=Path, help="Path to config file")
    parser.add_argument("--list-tools", action="store_true", help="List available tools")
    parser.add_argument("--list-resources", action="store_true", help="List available resources")
    
    args = parser.parse_args()
    
    if args.list_tools or args.list_resources:
        server = MCPServer(args.config)
        
        if args.list_tools:
            print("Available Tools:")
            for tool in server.tools.values():
                print(f"  - {tool.name}: {tool.description}")
        
        if args.list_resources:
            print("\nAvailable Resources:")
            for resource in server.resources.values():
                print(f"  - {resource.uri}: {resource.description}")
    else:
        run_server(args.port)


if __name__ == "__main__":
    main()
