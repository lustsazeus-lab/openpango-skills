# MCP (Model Context Protocol) Skill

Turns any OpenPango agent into an **MCP server**, making all installed skills available as tools in MCP-compatible clients (Claude Desktop, Cursor, Windsurf, etc.).

## Features

- **MCP Server**: Expose OpenPango skills as MCP tools via `stdio` transport
- **MCP Client**: Consume external MCP servers as OpenPango skills
- **Auto-discovery**: Scans installed skills and registers them as MCP tools
- **Config**: `mcp_config.json` for skill allowlists, auth tokens, and server settings

## Quick Start

### As a Server (expose skills to Claude Desktop)

```bash
# Register with Claude Desktop
python3 -m skills.mcp.mcp_server --register-claude

# Or run standalone
python3 -m skills.mcp.mcp_server
```

Add to Claude Desktop's `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "openpango": {
      "command": "python3",
      "args": ["-m", "skills.mcp.mcp_server"],
      "cwd": "/path/to/openpango-skills"
    }
  }
}
```

### As a Client (use external MCP tools)

```python
from skills.mcp.mcp_client import MCPClient

client = MCPClient("http://localhost:8080")
tools = client.list_tools()
result = client.call_tool("web_search", {"query": "OpenPango"})
```

## Configuration

Create `mcp_config.json` in your project root:
```json
{
  "server": {
    "name": "openpango-skills",
    "version": "1.0.0",
    "transport": "stdio"
  },
  "skills": {
    "allowlist": ["browser", "memory", "mining", "web3", "comms"],
    "expose_all": true
  },
  "auth": {
    "require_token": false,
    "token": null
  }
}
```
