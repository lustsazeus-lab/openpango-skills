#!/usr/bin/env python3
"""
mcp_server.py - MCP (Model Context Protocol) Server for OpenPango Skills.
Exposes OpenPango skills as MCP tools for use with Claude Desktop, Cursor, Windsurf, etc.
"""
import argparse
import json
import sys
import subprocess
from pathlib import Path
from typing import Any, Optional
import threading
import socket

# BASE_DIR should be the repository root (parent of skills/)
# When run as module from skills/mcp/, we need to go up 3 levels
_import_path = Path(__file__).resolve()
if _import_path.parent.name == "mcp":
    BASE_DIR = _import_path.parent.parent.parent
else:
    BASE_DIR = _import_path.parent.parent
SKILLS_DIR = BASE_DIR / "skills"

# MCP Protocol constants
MCP_VERSION = "2024-11-05"


class MCPServer:
    """MCP Server that exposes OpenPango skills as MCP tools."""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config = self._load_config(config_path)
        self.skills = self._discover_skills()
    
    def _load_config(self, config_path: Optional[Path]) -> dict:
        """Load MCP configuration."""
        if config_path is None:
            config_path = BASE_DIR / "mcp_config.json"
        
        if config_path.exists():
            with open(config_path) as f:
                return json.load(f)
        return {"allowed_skills": None, "auth_token": None}
    
    def _discover_skills(self) -> dict:
        """Auto-discover installed OpenPango skills."""
        skills = {}
        
        if not SKILLS_DIR.exists():
            return skills
        
        for skill_dir in SKILLS_DIR.iterdir():
            if not skill_dir.is_dir():
                continue
            if skill_dir.name.startswith('.') or skill_dir.name == '__pycache__':
                continue
            
            # Check if allowed
            allowed = self.config.get("allowed_skills")
            if allowed and skill_dir.name not in allowed:
                continue
            
            # Look for the main skill file
            skill_files = [
                skill_dir / f"{skill_dir.name}.py",
                skill_dir / f"{skill_dir.name}_manager.py",
                skill_dir / "skill.py",
                skill_dir / "SKILL.md"
            ]
            
            main_file = None
            for sf in skill_files:
                if sf.exists():
                    main_file = sf
                    break
            
            if main_file:
                skills[skill_dir.name] = {
                    "path": str(main_file),
                    "type": main_file.suffix
                }
        
        return skills
    
    def handle_request(self, request: dict) -> dict:
        """Handle incoming MCP request."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        handlers = {
            "initialize": self._handle_initialize,
            "tools/list": self._handle_tools_list,
            "tools/call": self._handle_tools_call,
            "resources/list": self._handle_resources_list,
            "resources/read": self._handle_resources_read,
        }
        
        handler = handlers.get(method)
        if handler:
            result = handler(params)
        else:
            return self._error_response(request_id, f"Unknown method: {method}")
        
        # Check if result is an error response
        if isinstance(result, dict) and "error" in result:
            return result
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }
    
    def _handle_initialize(self, params: dict) -> dict:
        """Handle initialize request."""
        return {
            "protocolVersion": MCP_VERSION,
            "serverInfo": {
                "name": "openpango-mcp-server",
                "version": "1.0.0"
            },
            "capabilities": {
                "tools": {"listChanged": True},
                "resources": {"subscribe": True, "listChanged": True}
            }
        }
    
    def _handle_tools_list(self, params: dict) -> dict:
        """Handle tools/list request."""
        tools = []
        
        for skill_name, skill_info in self.skills.items():
            # Create tool for each skill
            tool = {
                "name": f"skill_{skill_name}",
                "description": f"Execute OpenPango skill: {skill_name}",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "action": {
                            "type": "string",
                            "description": "Action to perform",
                            "enum": ["list", "execute"]
                        },
                        "params": {
                            "type": "object",
                            "description": "Skill-specific parameters"
                        }
                    },
                    "required": ["action"]
                }
            }
            tools.append(tool)
        
        return {"tools": tools}
    
    def _handle_tools_call(self, params: dict) -> dict:
        """Handle tools/call request."""
        name = params.get("name", "")
        arguments = params.get("arguments", {})
        
        if not name.startswith("skill_"):
            return self._error_response(None, f"Unknown tool: {name}")
        
        skill_name = name[6:]  # Remove "skill_" prefix
        
        if skill_name not in self.skills:
            return self._error_response(None, f"Unknown skill: {skill_name}")
        
        action = arguments.get("action", "list")
        skill_info = self.skills[skill_name]
        
        # Execute skill
        if skill_info["type"] == ".py":
            result = self._execute_skill_py(skill_name, action, arguments.get("params", {}))
        else:
            result = {"status": "error", "message": "Unsupported skill type"}
        
        return {"content": [{"type": "text", "text": json.dumps(result)}]}
    
    def _execute_skill_py(self, skill_name: str, action: str, params: dict) -> dict:
        """Execute a Python skill."""
        skill_path = SKILLS_DIR / skill_name / f"{skill_name}.py"
        
        if not skill_path.exists():
            return {"status": "error", "message": f"Skill file not found: {skill_path}"}
        
        try:
            # Try to import and call the skill
            import importlib.util
            spec = importlib.util.spec_from_file_location(skill_name, skill_path)
            module = importlib.util.module_from_spec(spec)
            
            # Check if skill has a main/run function
            if hasattr(module, "main"):
                result = module.main(action=action, **params)
                return {"status": "success", "result": result}
            elif hasattr(module, "run"):
                result = module.run(action=action, **params)
                return {"status": "success", "result": result}
            else:
                return {
                    "status": "success",
                    "skill": skill_name,
                    "action": action,
                    "message": f"Skill {skill_name} loaded but no main/run function found",
                    "actions_available": [a for a in dir(module) if not a.startswith('_')]
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def _handle_resources_list(self, params: dict) -> dict:
        """Handle resources/list request."""
        resources = []
        
        for skill_name in self.skills:
            resources.append({
                "uri": f"openpango://skill/{skill_name}",
                "name": skill_name,
                "description": f"OpenPango skill: {skill_name}",
                "mimeType": "application/json"
            })
        
        return {"resources": resources}
    
    def _handle_resources_read(self, params: dict) -> dict:
        """Handle resources/read request."""
        uri = params.get("uri", "")
        
        if not uri.startswith("openpango://skill/"):
            return self._error_response(None, f"Unknown resource: {uri}")
        
        skill_name = uri[18:]  # Remove "openpango://skill/" prefix
        
        if skill_name not in self.skills:
            return self._error_response(None, f"Unknown skill: {skill_name}")
        
        skill_info = self.skills[skill_name]
        
        with open(skill_info["path"]) as f:
            content = f.read()
        
        return {
            "contents": [{
                "uri": uri,
                "mimeType": "text/plain",
                "text": content
            }]
        }
    
    def _error_response(self, request_id: Optional[Any], message: str) -> dict:
        """Create error response."""
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": message
            }
        }


def main():
    """Run MCP server in stdio mode."""
    parser = argparse.ArgumentParser(description="OpenPango MCP Server")
    parser.add_argument("--config", type=Path, help="Path to mcp_config.json")
    args = parser.parse_args()
    
    server = MCPServer(args.config)
    
    # Read requests from stdin, write to stdout
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        
        try:
            request = json.loads(line)
            response = server.handle_request(request)
            print(json.dumps(response), flush=True)
        except json.JSONDecodeError:
            print(json.dumps({
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": "Parse error"}
            }), flush=True)


if __name__ == "__main__":
    main()
