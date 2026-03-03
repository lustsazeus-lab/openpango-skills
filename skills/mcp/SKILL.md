# MCP (Model Context Protocol) Skill

**Category:** integration  
**Tier:** utility  
**Bounty:** $5.00

## Overview

This skill provides MCP (Model Context Protocol) integration for OpenPango agents. MCP is the emerging standard for LLM tool integration, enabling OpenPango to work with Claude Desktop, Cursor, Windsurf, and other MCP-compatible AI IDEs and platforms.

## Components

### mcp_server.py

Exposes OpenPango skills as MCP tools. Run as a stdio server to provide tools to MCP clients.

**Features:**
- Auto-discovers installed OpenPango skills
- Supports `tools/list`, `tools/call`, `resources/list`, `resources/read`
- Configurable skill allowlist via `mcp_config.json`
- Authentication token support

**Usage:**
```bash
python -m skills.mcp.mcp_server
```

**MCP Configuration (mcp_config.json):**
```json
{
  "allowed_skills": ["memory", "browser", "github"],
  "auth_token": "your-token-here"
}
```

### mcp_client.py

Consumes external MCP servers as OpenPango skills.

**Features:**
- Connect to any MCP-compatible server
- Pool management for multiple server connections
- Tool and resource listing
- Resource reading support

**Usage:**
```python
from skills.mcp.mcp_client import MCPClient, MCPClientPool

# Single server
client = MCPClient(["python", "mcp_server.py"])
client.start()
tools = client.list_tools()
result = client.call_tool("my_tool", {"arg": "value"})
client.stop()

# Multiple servers
pool = MCPClientPool()
pool.add_server("server1", ["node", "server.js"])
pool.add_server("server2", ["python", "another_server.py"])
all_tools = pool.list_all_tools()
pool.close_all()
```

## MCP Protocol

The implementation follows the [Model Context Protocol specification](https://modelcontextprotocol.io):

- **JSON-RPC 2.0** messaging over stdio
- **Initialize**: Handshake with server capabilities
- **Tools**: List and call external tools
- **Resources**: List and read external resources

## Examples

### Running as MCP Server

Configure in Claude Desktop (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "openpango": {
      "command": "python",
      "args": ["-m", "skills.mcp.mcp_server"]
    }
  }
}
```

### Connecting to External Server

```python
from skills.mcp.mcp_client import MCPClient

# Connect to a filesystem MCP server
client = MCPClient(["npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp"])
client.start()

# List and use tools
for tool in client.list_tools():
    print(f"{tool.name}: {tool.description}")

client.stop()
```

## Testing

Run the test suite:
```bash
python -m pytest tests/test_mcp.py -v
```

## Requirements

- Python 3.10+
- External MCP servers (optional, for client functionality)

## Notes

- MCP uses stdio by default for secure local communication
- Server auto-discovers skills from the `skills/` directory
- Client supports multiple concurrent server connections
