#!/usr/bin/env python3
"""
Tests for MCP Server and Client.

These tests use mocked MCP protocol messages to verify functionality.
"""

import json
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import sys
import tempfile
import os

# Add skills directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server import (
    MCPServer, MCPTool, MCPResource, MCPError,
    ERROR_PARSE_ERROR, ERROR_INVALID_REQUEST, ERROR_METHOD_NOT_FOUND
)
from mcp_client import (
    MCPClient, MCPClientRegistry, MCPToolDefinition, MCPResource
)


class TestMCPServer(unittest.TestCase):
    """Tests for MCP Server."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.server = MCPServer()
    
    def test_server_initialization(self):
        """Test server initializes correctly."""
        self.assertIsNotNone(self.server)
        self.assertIsNotNone(self.server.config)
        self.assertEqual(self.server.config.get("port", 8765), 8765)
    
    def test_handle_initialize(self):
        """Test initialize request."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {}
        }
        
        response = self.server.handle_request(request)
        
        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], 1)
        self.assertIn("result", response)
        self.assertIn("protocolVersion", response["result"])
        self.assertIn("serverInfo", response["result"])
    
    def test_handle_ping(self):
        """Test ping request."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "ping"
        }
        
        response = self.server.handle_request(request)
        
        self.assertEqual(response["result"]["pong"], True)
    
    def test_handle_tools_list(self):
        """Test tools/list request."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list"
        }
        
        response = self.server.handle_request(request)
        
        self.assertIn("result", response)
        self.assertIn("tools", response["result"])
        # Should have discovered some tools (skills)
        self.assertIsInstance(response["result"]["tools"], list)
    
    def test_handle_tools_call(self):
        """Test tools/call request."""
        # First get list of available tools
        list_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list"
        }
        list_response = self.server.handle_request(list_request)
        tools = list_response["result"]["tools"]
        
        if tools:
            # Try to call the first tool
            tool_name = tools[0]["name"]
            call_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": {"action": "list"}
                }
            }
            
            response = self.server.handle_request(call_request)
            self.assertIn("result", response)
            self.assertIn("content", response["result"])
    
    def test_handle_tools_call_invalid_tool(self):
        """Test tools/call with invalid tool name."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "nonexistent_tool",
                "arguments": {}
            }
        }
        
        response = self.server.handle_request(request)
        
        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], ERROR_METHOD_NOT_FOUND)
    
    def test_handle_resources_list(self):
        """Test resources/list request."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "resources/list"
        }
        
        response = self.server.handle_request(request)
        
        self.assertIn("result", response)
        self.assertIn("resources", response["result"])
        self.assertIsInstance(response["result"]["resources"], list)
    
    def test_handle_resources_read(self):
        """Test resources/read request."""
        # First get list of resources
        list_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "resources/list"
        }
        list_response = self.server.handle_request(list_request)
        resources = list_response["result"]["resources"]
        
        if resources:
            uri = resources[0]["uri"]
            read_request = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "resources/read",
                "params": {"uri": uri}
            }
            
            response = self.server.handle_request(read_request)
            self.assertIn("result", response)
    
    def test_handle_resources_read_invalid(self):
        """Test resources/read with invalid URI."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "resources/read",
            "params": {"uri": "nonexistent://resource"}
        }
        
        response = self.server.handle_request(request)
        
        self.assertIn("error", response)
    
    def test_handle_invalid_method(self):
        """Test handling of invalid method."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "invalid_method"
        }
        
        response = self.server.handle_request(request)
        
        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], ERROR_METHOD_NOT_FOUND)
    
    def test_skill_discovery(self):
        """Test that skills are discovered."""
        # Server should have discovered skills from the skills directory
        self.assertIsInstance(self.server.tools, dict)
        self.assertIsInstance(self.server.resources, dict)
    
    def test_error_response_format(self):
        """Test error response format."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "nonexistent"
            }
        }
        
        response = self.server.handle_request(request)
        
        self.assertIn("error", response)
        error = response["error"]
        self.assertIn("code", error)
        self.assertIn("message", error)


class TestMCPClient(unittest.TestCase):
    """Tests for MCP Client."""
    
    def test_client_initialization(self):
        """Test client initializes with URL."""
        client = MCPClient("http://localhost:8765")
        
        self.assertEqual(client.server_url, "http://localhost:8765")
        self.assertIsNone(client.auth_token)
        self.assertFalse(client._initialized)
    
    def test_client_with_auth(self):
        """Test client with authentication."""
        client = MCPClient(
            "http://localhost:8765",
            auth_token="test-token"
        )
        
        self.assertEqual(client.auth_token, "test-token")
    
    @patch('urllib.request.urlopen')
    def test_initialize(self, mock_urlopen):
        """Test client initialization."""
        # Mock response
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "test-server",
                    "version": "1.0.0"
                }
            }
        }).encode('utf-8')
        mock_urlopen.return_value = __enter__ = mock_response
        
        client = MCPClient("http://localhost:8765")
        result = client.initialize()
        
        self.assertIn("protocolVersion", result)
        self.assertTrue(client._initialized)
    
    @patch('urllib.request.urlopen')
    def test_list_tools(self, mock_urlopen):
        """Test listing tools."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "tools": [
                    {
                        "name": "test_tool",
                        "description": "A test tool",
                        "inputSchema": {"type": "object"}
                    }
                ]
            }
        }).encode('utf-8')
        mock_urlopen.return_value = mock_response
        
        client = MCPClient("http://localhost:8765")
        tools = client.list_tools()
        
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0].name, "test_tool")
    
    @patch('urllib.request.urlopen')
    def test_call_tool(self, mock_urlopen):
        """Test calling a tool."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "content": [{"type": "text", "text": "success"}]
            }
        }).encode('utf-8')
        mock_urlopen.return_value = mock_response
        
        client = MCPClient("http://localhost:8765")
        client._initialized = True
        result = client.call_tool("test_tool", {"arg": "value"})
        
        self.assertIn("content", result)
    
    @patch('urllib.request.urlopen')
    def test_ping(self, mock_urlopen):
        """Test ping."""
        mock_response = Mock()
        mock_response.read.return_value = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"pong": True}
        }).encode('utf-8')
        mock_urlopen.return_value = mock_response
        
        client = MCPClient("http://localhost:8765")
        result = client.ping()
        
        self.assertTrue(result)
    
    @patch('urllib.request.urlopen')
    def test_connection_error(self, mock_urlopen):
        """Test connection error handling."""
        import urllib.error
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")
        
        client = MCPClient("http://localhost:8765")
        
        with self.assertRaises(ConnectionError):
            client.ping()


class TestMCPClientRegistry(unittest.TestCase):
    """Tests for MCP Client Registry."""
    
    def test_registry_initialization(self):
        """Test registry initializes empty."""
        registry = MCPClientRegistry()
        
        self.assertIsInstance(registry.clients, dict)
        self.assertEqual(len(registry.clients), 0)
    
    def test_add_server(self):
        """Test adding a server."""
        registry = MCPClientRegistry()
        registry.add_server("test", "http://localhost:8765")
        
        self.assertIn("test", registry.clients)
    
    def test_remove_server(self):
        """Test removing a server."""
        registry = MCPClientRegistry()
        registry.add_server("test", "http://localhost:8765")
        registry.remove_server("test")
        
        self.assertNotIn("test", registry.clients)
    
    def test_get_client(self):
        """Test getting a client."""
        registry = MCPClientRegistry()
        registry.add_server("test", "http://localhost:8765")
        
        client = registry.get_client("test")
        
        self.assertIsNotNone(client)
        self.assertIsInstance(client, MCPClient)
    
    def test_get_client_not_found(self):
        """Test getting non-existent client."""
        registry = MCPClientRegistry()
        
        client = registry.get_client("nonexistent")
        
        self.assertIsNone(client)


class TestMCPProtocol(unittest.TestCase):
    """Tests for MCP protocol compliance."""
    
    def test_jsonrpc_version(self):
        """Test JSON-RPC version handling."""
        from mcp_server import JSONRPC_VERSION
        self.assertEqual(JSONRPC_VERSION, "2.0")
    
    def test_error_codes(self):
        """Test MCP error codes."""
        self.assertEqual(ERROR_PARSE_ERROR, -32700)
        self.assertEqual(ERROR_INVALID_REQUEST, -32600)
        self.assertEqual(ERROR_METHOD_NOT_FOUND, -32601)
    
    def test_tool_definition(self):
        """Test tool definition structure."""
        tool = MCPTool(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object"}
        )
        
        self.assertEqual(tool.name, "test_tool")
        self.assertEqual(tool.description, "A test tool")
        self.assertEqual(tool.input_schema["type"], "object")
    
    def test_resource_definition(self):
        """Test resource definition structure."""
        resource = MCPResource(
            uri="test://resource",
            name="test_resource",
            description="A test resource"
        )
        
        self.assertEqual(resource.uri, "test://resource")
        self.assertEqual(resource.name, "test_resource")
        self.assertEqual(resource.mime_type, "application/json")


class TestMCPWithMockedProtocol(unittest.TestCase):
    """Tests using mocked MCP protocol messages."""
    
    @patch('urllib.request.urlopen')
    def test_full_tool_lifecycle(self, mock_urlopen):
        """Test complete tool lifecycle: initialize -> list -> call."""
        # Mock initialize
        init_response = Mock()
        init_response.read.return_value = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "test", "version": "1.0.0"},
                "capabilities": {}
            }
        }).encode('utf-8')
        
        # Mock tools/list
        tools_response = Mock()
        tools_response.read.return_value = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "tools": [
                    {"name": "echo", "description": "Echo back input", "inputSchema": {}}
                ]
            }
        }).encode('utf-8')
        
        # Mock tools/call
        call_response = Mock()
        call_response.read.return_value = json.dumps({
            "jsonrpc": "2.0",
            "id": 3,
            "result": {
                "content": [{"type": "text", "text": "hello"}]
            }
        }).encode('utf-8')
        
        mock_urlopen.side_effect = [init_response, tools_response, call_response]
        
        client = MCPClient("http://localhost:8765")
        
        # Initialize
        info = client.initialize()
        self.assertEqual(info["serverInfo"]["name"], "test")
        
        # List tools
        tools = client.list_tools()
        self.assertEqual(len(tools), 1)
        
        # Call tool
        result = client.call_tool("echo", {"text": "hello"})
        self.assertIn("content", result)


if __name__ == "__main__":
    unittest.main()
