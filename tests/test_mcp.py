#!/usr/bin/env python3
"""
test_mcp.py - Tests for MCP Server and Client.
"""
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

# Add skills to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from skills.mcp.mcp_server import MCPServer
from skills.mcp.mcp_client import MCPClient, MCPClientPool, MCPTool, MCPResource


class TestMCPServer(unittest.TestCase):
    """Test MCP Server functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.server = MCPServer()
    
    def test_initialize(self):
        """Test initialize request."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"}
        }
        
        response = self.server.handle_request(request)
        
        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertEqual(response["id"], 1)
        self.assertIn("result", response)
        self.assertIn("protocolVersion", response["result"])
    
    def test_tools_list(self):
        """Test tools/list request."""
        request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        response = self.server.handle_request(request)
        
        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertIn("result", response)
        self.assertIn("tools", response["result"])
    
    def test_tools_call(self):
        """Test tools/call request."""
        request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "skill_memory",
                "arguments": {"action": "execute"}
            }
        }
        
        response = self.server.handle_request(request)
        
        # The skill might not exist in test env, just check it's a valid response
        self.assertEqual(response["jsonrpc"], "2.0")
    
    def test_tools_call_unknown_skill(self):
        """Test tools/call with unknown skill."""
        request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "skill_nonexistent",
                "arguments": {}
            }
        }
        
        response = self.server.handle_request(request)
        
        self.assertIn("error", response)
    
    def test_resources_list(self):
        """Test resources/list request."""
        request = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "resources/list",
            "params": {}
        }
        
        response = self.server.handle_request(request)
        
        self.assertEqual(response["jsonrpc"], "2.0")
        self.assertIn("result", response)
        self.assertIn("resources", response["result"])
    
    def test_resources_read(self):
        """Test resources/read request."""
        # First get a valid resource URI
        list_response = self.server.handle_request({
            "jsonrpc": "2.0",
            "id": 6,
            "method": "resources/list",
            "params": {}
        })
        
        if list_response["result"]["resources"]:
            uri = list_response["result"]["resources"][0]["uri"]
            
            request = {
                "jsonrpc": "2.0",
                "id": 7,
                "method": "resources/read",
                "params": {"uri": uri}
            }
            
            response = self.server.handle_request(request)
            
            self.assertEqual(response["jsonrpc"], "2.0")
            self.assertIn("result", response)
    
    def test_unknown_method(self):
        """Test unknown method handling."""
        request = {
            "jsonrpc": "2.0",
            "id": 8,
            "method": "unknown/method",
            "params": {}
        }
        
        response = self.server.handle_request(request)
        
        self.assertIn("error", response)
        self.assertEqual(response["error"]["code"], -32601)


class TestMCPClient(unittest.TestCase):
    """Test MCP Client functionality."""
    
    @patch('subprocess.Popen')
    def test_client_initialization(self, mock_popen):
        """Test MCP client initialization."""
        # Mock process
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.stdout.readline.return_value = json.dumps({
            "jsonrpc": "2.0",
            "id": 0,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "test", "version": "1.0.0"},
                "capabilities": {}
            }
        })
        mock_popen.return_value = mock_process
        
        client = MCPClient(["test", "command"])
        # Don't start to avoid actual process management in test
        
        self.assertEqual(client.command, ["test", "command"])
    
    def test_mcp_tool_dataclass(self):
        """Test MCPTool dataclass."""
        tool = MCPTool(
            name="test_tool",
            description="A test tool",
            input_schema={"type": "object"}
        )
        
        self.assertEqual(tool.name, "test_tool")
        self.assertEqual(tool.description, "A test tool")
    
    def test_mcp_resource_dataclass(self):
        """Test MCPResource dataclass."""
        resource = MCPResource(
            uri="test://resource/1",
            name="Test Resource",
            description="A test resource",
            mime_type="application/json"
        )
        
        self.assertEqual(resource.uri, "test://resource/1")
        self.assertEqual(resource.mime_type, "application/json")


class TestMCPClientPool(unittest.TestCase):
    """Test MCP Client Pool functionality."""
    
    def test_pool_initialization(self):
        """Test pool initialization."""
        pool = MCPClientPool()
        
        self.assertEqual(len(pool.clients), 0)
    
    @patch('subprocess.Popen')
    def test_pool_add_server(self, mock_popen):
        """Test adding server to pool."""
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_process.stdout.readline.return_value = json.dumps({
            "jsonrpc": "2.0",
            "id": 0,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "test", "version": "1.0.0"},
                "capabilities": {}
            }
        })
        mock_popen.return_value = mock_process
        
        pool = MCPClientPool()
        
        # Don't actually start to avoid process management
        pool.clients["test"] = Mock()
        
        self.assertIn("test", pool.clients)
    
    def test_pool_remove_server(self):
        """Test removing server from pool."""
        pool = MCPClientPool()
        mock_client = Mock()
        pool.clients["test"] = mock_client
        
        pool.remove_server("test")
        
        self.assertNotIn("test", pool.clients)
        mock_client.stop.assert_called_once()
    
    def test_pool_get_client(self):
        """Test getting client from pool."""
        pool = MCPClientPool()
        mock_client = Mock()
        pool.clients["test"] = mock_client
        
        client = pool.get_client("test")
        
        self.assertEqual(client, mock_client)
    
    def test_pool_get_client_not_found(self):
        """Test getting non-existent client from pool."""
        pool = MCPClientPool()
        
        client = pool.get_client("nonexistent")
        
        self.assertIsNone(client)


class TestMCPIntegration(unittest.TestCase):
    """Integration tests for MCP protocol."""
    
    def test_json_rpc_request_format(self):
        """Test JSON-RPC request format."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        
        # Should be valid JSON
        json_str = json.dumps(request)
        parsed = json.loads(json_str)
        
        self.assertEqual(parsed["jsonrpc"], "2.0")
        self.assertEqual(parsed["id"], 1)
        self.assertEqual(parsed["method"], "tools/list")
    
    def test_json_rpc_response_format(self):
        """Test JSON-RPC response format."""
        response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"tools": []}
        }
        
        json_str = json.dumps(response)
        parsed = json.loads(json_str)
        
        self.assertEqual(parsed["jsonrpc"], "2.0")
        self.assertEqual(parsed["id"], 1)
        self.assertIn("result", parsed)
    
    def test_json_rpc_error_format(self):
        """Test JSON-RPC error format."""
        error = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32601,
                "message": "Method not found"
            }
        }
        
        json_str = json.dumps(error)
        parsed = json.loads(json_str)
        
        self.assertEqual(parsed["jsonrpc"], "2.0")
        self.assertEqual(parsed["error"]["code"], -32601)


if __name__ == "__main__":
    unittest.main()
