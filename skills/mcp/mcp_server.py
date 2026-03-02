#!/usr/bin/env python3
"""
mcp_server.py — OpenPango MCP Server.

Exposes installed OpenPango skills as MCP (Model Context Protocol) tools.
Compatible with Claude Desktop, Cursor, Windsurf, and any MCP client.

Transport: stdio (reads JSON-RPC from stdin, writes to stdout).

Usage:
    python3 -m skills.mcp.mcp_server
    python3 -m skills.mcp.mcp_server --register-claude
"""

import json
import sys
import os
import logging
import importlib
import pkgutil
from pathlib import Path
from typing import Dict, List, Any, Optional

logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                    format='%(asctime)s [MCP] %(levelname)s: %(message)s')
logger = logging.getLogger("MCPServer")

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "openpango-skills"
SERVER_VERSION = "1.0.0"

SKILLS_DIR = Path(__file__).parent.parent


def discover_skills() -> Dict[str, Dict]:
    """Auto-discover installed OpenPango skills by scanning the skills directory."""
    skills = {}
    if not SKILLS_DIR.is_dir():
        return skills

    for item in sorted(SKILLS_DIR.iterdir()):
        if not item.is_dir() or item.name.startswith(("_", ".")):
            continue
        skill_md = item / "SKILL.md"
        init_py = item / "__init__.py"
        if skill_md.exists() or init_py.exists():
            description = f"OpenPango {item.name} skill"
            if skill_md.exists():
                # Extract first non-empty, non-header line as description
                for line in skill_md.read_text().splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        description = line[:200]
                        break
            skills[item.name] = {
                "name": f"openpango_{item.name}",
                "description": description,
                "path": str(item),
                "has_init": init_py.exists(),
            }
    return skills


def load_config() -> Dict:
    """Load MCP configuration from mcp_config.json if it exists."""
    config_path = SKILLS_DIR.parent / "mcp_config.json"
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return {
        "server": {"name": SERVER_NAME, "version": SERVER_VERSION, "transport": "stdio"},
        "skills": {"expose_all": True, "allowlist": []},
        "auth": {"require_token": False, "token": None},
    }


def build_tool_list(skills: Dict[str, Dict], config: Dict) -> List[Dict]:
    """Build the MCP tools/list response from discovered skills."""
    tools = []
    allowlist = config.get("skills", {}).get("allowlist", [])
    expose_all = config.get("skills", {}).get("expose_all", True)

    for name, info in skills.items():
        if not expose_all and name not in allowlist:
            continue
        tools.append({
            "name": info["name"],
            "description": info["description"],
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": f"The action to perform with the {name} skill",
                    },
                    "params": {
                        "type": "object",
                        "description": "Parameters for the action",
                        "additionalProperties": True,
                    },
                },
                "required": ["action"],
            },
        })

    # Add built-in tools
    tools.append({
        "name": "openpango_pool_stats",
        "description": "Get real-time statistics from the OpenPango mining pool",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    })
    tools.append({
        "name": "openpango_list_skills",
        "description": "List all installed OpenPango skills",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    })

    return tools


def handle_tool_call(name: str, arguments: Dict, skills: Dict) -> Dict:
    """Execute a tool call and return the result."""
    if name == "openpango_list_skills":
        skill_list = [{"name": k, "path": v["path"], "description": v["description"]}
                      for k, v in skills.items()]
        return {"content": [{"type": "text", "text": json.dumps(skill_list, indent=2)}]}

    if name == "openpango_pool_stats":
        try:
            sys.path.insert(0, str(SKILLS_DIR.parent))
            from skills.mining.mining_pool import MiningPool
            pool = MiningPool()
            stats = pool.get_pool_stats()
            return {"content": [{"type": "text", "text": json.dumps(stats, indent=2)}]}
        except Exception as e:
            return {"content": [{"type": "text", "text": f"Error: {e}"}], "isError": True}

    # Generic skill execution
    skill_name = name.replace("openpango_", "")
    if skill_name not in skills:
        return {"content": [{"type": "text", "text": f"Unknown skill: {skill_name}"}], "isError": True}

    skill_info = skills[skill_name]
    action = arguments.get("action", "help")
    params = arguments.get("params", {})

    try:
        if skill_info["has_init"]:
            module = importlib.import_module(f"skills.{skill_name}")
            if hasattr(module, "execute"):
                result = module.execute(action, **params)
                return {"content": [{"type": "text", "text": str(result)}]}

        return {"content": [{"type": "text", "text": f"Skill '{skill_name}' loaded. Action: {action}. "
                             f"Params: {json.dumps(params)}. (Direct execution not available — "
                             f"use the skill's Python API directly.)"}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": f"Error executing {skill_name}: {e}"}], "isError": True}


def handle_request(request: Dict, skills: Dict, config: Dict) -> Optional[Dict]:
    """Handle a single JSON-RPC request and return a response."""
    method = request.get("method")
    req_id = request.get("id")
    params = request.get("params", {})

    # Notifications (no id) don't get responses
    if req_id is None and method == "notifications/initialized":
        logger.info("Client initialized")
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False},
                },
                "serverInfo": {
                    "name": config.get("server", {}).get("name", SERVER_NAME),
                    "version": config.get("server", {}).get("version", SERVER_VERSION),
                },
            },
        }

    if method == "tools/list":
        tools = build_tool_list(skills, config)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": tools},
        }

    if method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        result = handle_tool_call(tool_name, arguments, skills)
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": result,
        }

    if method == "resources/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"resources": []},
        }

    if method == "resources/read":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": "Resource not found"},
        }

    # Unknown method
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def register_claude_desktop():
    """Print the Claude Desktop config snippet for this server."""
    project_root = str(SKILLS_DIR.parent)
    config = {
        "mcpServers": {
            "openpango": {
                "command": "python3",
                "args": ["-m", "skills.mcp.mcp_server"],
                "cwd": project_root,
            }
        }
    }
    print("\n📋 Add this to your Claude Desktop config:")
    print(f"   ~/Library/Application Support/Claude/claude_desktop_config.json\n")
    print(json.dumps(config, indent=2))
    print(f"\n✅ OpenPango MCP server configured at: {project_root}")


def run_stdio_server():
    """Run the MCP server using stdio transport (JSON-RPC over stdin/stdout)."""
    config = load_config()
    skills = discover_skills()
    logger.info(f"MCP Server starting — {len(skills)} skills discovered")

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            response = handle_request(request, skills, config)
            if response:
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
            error_response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"},
            }
            sys.stdout.write(json.dumps(error_response) + "\n")
            sys.stdout.flush()
        except Exception as e:
            logger.error(f"Error handling request: {e}")


if __name__ == "__main__":
    if "--register-claude" in sys.argv:
        register_claude_desktop()
    elif "--list-tools" in sys.argv:
        skills = discover_skills()
        config = load_config()
        tools = build_tool_list(skills, config)
        print(json.dumps({"tools": tools}, indent=2))
    else:
        run_stdio_server()
