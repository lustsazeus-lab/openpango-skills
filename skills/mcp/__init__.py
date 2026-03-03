"""
MCP (Model Context Protocol) skill for OpenPango.

This module provides:
- MCP Server: Expose OpenPango skills as MCP tools
- MCP Client: Consume external MCP servers as OpenPango skills
"""

from .mcp_server import MCPServer, MCPTool, MCPResource, MCPError, run_server
from .mcp_client import MCPClient, MCPClientRegistry, MCPToolDefinition

__all__ = [
    "MCPServer",
    "MCPTool", 
    "MCPResource",
    "MCPError",
    "run_server",
    "MCPClient",
    "MCPClientRegistry",
    "MCPToolDefinition"
]

__version__ = "1.0.0"
