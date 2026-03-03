---
name: mcp
description: "MCP (Model Context Protocol) server and client for exposing and consuming MCP-compatible tools."
user-invocable: true
metadata: {"openclaw":{"emoji":"🔌","skillKey":"openpango-mcp"}}
---

## Overview

This skill provides MCP (Model Context Protocol) integration for OpenPango, enabling:
- **Server**: Expose OpenPango skills as MCP tools for external MCP clients
- **Client**: Connect to external MCP servers and use their tools as OpenPango skills

[MCP](https://modelcontextprotocol.io) is the emerging standard for LLM tool integration, compatible with Claude Desktop, Cursor, Windsurf, and other AI IDEs.

## MCP Server

### Start the Server

```bash
python3 skills/mcp/mcp_server.py --port 8765
```

### List Available Tools

```bash
python3 skills/mcp/mcp_server.py --list-tools
```

### List Available Resources

```bash
python3 skills/mcp/mcp_server.py --list-resources
```

### Configuration

Create `~/.openclaw/workspace/mcp_config.json`:

```json
{
  "allowlist": ["vision", "browser", "a2a"],
  "auth_tokens": {
    "default": "your-secret-token"
  },
  "port": 8765
}
```

### Server Endpoints

- `POST /mcp` - MCP JSON-RPC endpoint
- `GET /health` - Health check

### Supported Methods

| Method | Description |
|--------|-------------|
| `initialize` | Initialize the MCP session |
| `tools/list` | List available tools |
| `tools/call` | Call a tool |
| `resources/list` | List available resources |
| `resources/read` | Read a resource |
| `ping` | Health check |

## MCP Client

### Connect to an MCP Server

```bash
python3 skills/mcp/mcp_client.py http://localhost:8765 --list-tools
```

### List Server Tools

```bash
python3 skills/mcp/mcp_client.py http://localhost:8765 --list-tools
```

### List Server Resources

```bash
python3 skills/mcp/mcp_client.py http://localhost:8765 --list-resources
```

### Call a Tool

```bash
python3 skills/mcp/mcp_client.py http://localhost:8765 \
  --call skill_browser \
  --args '{"action": "info"}'
```

### Read a Resource

```bash
python3 skills/mcp/mcp_client.py http://localhost:8765 \
  --read "skill://browser/info"
```

### Ping Server

```bash
python3 skills/mcp/mcp_client.py http://localhost:8765 --ping
```

### Get Server Info

```bash
python3 skills/mcp/mcp_client.py http://localhost:8765 --info
```

### Authentication

```bash
python3 skills/mcp/mcp_client.py http://localhost:8765 \
  --auth-token your-secret-token \
  --list-tools
```

## MCP as OpenPango Skills

### Auto-Discovery

The MCP server automatically discovers installed OpenPango skills and exposes them as MCP tools:

```
skills/vision      → tools/skill_vision
skills/browser     → tools/skill_browser
skills/a2a        → tools/skill_a2a
```

### Tool Structure

Each skill is exposed with the following schema:

```json
{
  "name": "skill_vision",
  "description": "Analyze images...",
  "inputSchema": {
    "type": "object",
    "properties": {
      "action": {
        "type": "string",
        "enum": ["list", "info", "execute"]
      },
      "skill_name": {"type": "string"},
      "params": {"type": "object"}
    }
  }
}
```

### Resource URIs

Skills are also available as resources:

- `skill://{skill_name}/info` - Get skill information

## Usage Examples

### Expose Skills to Claude Desktop

1. Add to your MCP settings (Claude Desktop):

```json
{
  "mcpServers": {
    "openpango": {
      "command": "python3",
      "args": ["path/to/skills/mcp/mcp_server.py"]
    }
  }
}
```

2. Claude Desktop will now have access to all OpenPango skills as tools.

### Use External MCP Server in OpenPango

1. Configure server in `~/.openclaw/workspace/mcp_servers.json`:

```json
{
  "servers": {
    "filesystem": {
      "url": "http://localhost:3000",
      "auth_token": "optional-token"
    }
  }
}
```

2. Use the client in your agent:

```python
from skills.mcp import MCPClient

client = MCPClient("http://localhost:3000")
client.initialize()
tools = client.list_tools()
result = client.call_tool("read_file", {"path": "/tmp/test.txt"})
```

## Error Handling

All operations return JSON. Check for `error` field:

```json
{
  "error": "Tool not found",
  "details": "skill_foo does not exist"
}
```

## Integration with Other Skills

### A2A Integration

The MCP skill works with A2A for agent-to-agent communication:

```python
from skills.a2a import message_bus

# Send MCP server info to another agent
message_bus.send_message({
    "type": "task_request",
    "to": "agent_planner",
    "payload": {
        "action": "use_mcp_tools",
        "tools": ["skill_vision", "skill_browser"]
    }
})
```

### Memory Integration

Store MCP server configurations in memory:

```python
from skills.memory import memory

memory.save({
    "type": "mcp_server",
    "name": "production",
    "url": "https://mcp.example.com",
    "tools": ["read_file", "write_file", "run_command"]
})
```
