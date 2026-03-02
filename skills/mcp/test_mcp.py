#!/usr/bin/env python3
"""Tests for the MCP server and client modules."""

import json
import sys
import os
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from skills.mcp.mcp_server import (
    discover_skills,
    load_config,
    build_tool_list,
    handle_tool_call,
    handle_request,
)
from skills.mcp.mcp_client import MCPClient


class TestSkillDiscovery(unittest.TestCase):
    def test_discovers_skills(self):
        skills = discover_skills()
        self.assertIsInstance(skills, dict)
        self.assertTrue(len(skills) > 0, "Should discover at least one skill")

    def test_skill_has_required_fields(self):
        skills = discover_skills()
        for name, info in skills.items():
            self.assertIn("name", info)
            self.assertIn("description", info)
            self.assertIn("path", info)
            self.assertTrue(info["name"].startswith("openpango_"))

    def test_mining_skill_discovered(self):
        skills = discover_skills()
        self.assertIn("mining", skills)

    def test_mcp_skill_discovered(self):
        skills = discover_skills()
        self.assertIn("mcp", skills)


class TestConfig(unittest.TestCase):
    def test_load_default_config(self):
        config = load_config()
        self.assertIn("server", config)
        self.assertIn("skills", config)
        self.assertIn("auth", config)

    def test_default_config_exposes_all(self):
        config = load_config()
        self.assertTrue(config["skills"].get("expose_all", True))


class TestToolList(unittest.TestCase):
    def test_builds_tool_list(self):
        skills = discover_skills()
        config = load_config()
        tools = build_tool_list(skills, config)
        self.assertIsInstance(tools, list)
        # Should have at least skill count + 2 built-in tools
        self.assertTrue(len(tools) >= 3)

    def test_built_in_tools_present(self):
        skills = discover_skills()
        config = load_config()
        tools = build_tool_list(skills, config)
        tool_names = [t["name"] for t in tools]
        self.assertIn("openpango_pool_stats", tool_names)
        self.assertIn("openpango_list_skills", tool_names)

    def test_tool_has_input_schema(self):
        skills = discover_skills()
        config = load_config()
        tools = build_tool_list(skills, config)
        for tool in tools:
            self.assertIn("inputSchema", tool)
            self.assertEqual(tool["inputSchema"]["type"], "object")

    def test_allowlist_filter(self):
        skills = discover_skills()
        config = {"skills": {"expose_all": False, "allowlist": ["mining"]}}
        tools = build_tool_list(skills, config)
        skill_tools = [t for t in tools if not t["name"].startswith("openpango_pool") and not t["name"].startswith("openpango_list")]
        self.assertEqual(len(skill_tools), 1)
        self.assertEqual(skill_tools[0]["name"], "openpango_mining")


class TestToolExecution(unittest.TestCase):
    def test_list_skills_tool(self):
        skills = discover_skills()
        result = handle_tool_call("openpango_list_skills", {}, skills)
        self.assertIn("content", result)
        content = json.loads(result["content"][0]["text"])
        self.assertIsInstance(content, list)
        self.assertTrue(len(content) > 0)

    def test_pool_stats_tool(self):
        skills = discover_skills()
        result = handle_tool_call("openpango_pool_stats", {}, skills)
        self.assertIn("content", result)
        # Should return valid JSON with pool stats
        content = json.loads(result["content"][0]["text"])
        self.assertIn("total_miners", content)

    def test_unknown_tool(self):
        result = handle_tool_call("nonexistent_tool", {}, {})
        self.assertTrue(result.get("isError", False))


class TestRequestHandling(unittest.TestCase):
    def setUp(self):
        self.skills = discover_skills()
        self.config = load_config()

    def test_initialize(self):
        response = handle_request(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
            self.skills, self.config
        )
        self.assertEqual(response["id"], 1)
        self.assertIn("protocolVersion", response["result"])
        self.assertIn("capabilities", response["result"])
        self.assertIn("serverInfo", response["result"])

    def test_tools_list(self):
        response = handle_request(
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            self.skills, self.config
        )
        self.assertEqual(response["id"], 2)
        self.assertIn("tools", response["result"])

    def test_tools_call(self):
        response = handle_request(
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
             "params": {"name": "openpango_list_skills", "arguments": {}}},
            self.skills, self.config
        )
        self.assertEqual(response["id"], 3)
        self.assertIn("content", response["result"])

    def test_unknown_method(self):
        response = handle_request(
            {"jsonrpc": "2.0", "id": 4, "method": "unknown/method"},
            self.skills, self.config
        )
        self.assertIn("error", response)

    def test_notification_returns_none(self):
        response = handle_request(
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            self.skills, self.config
        )
        self.assertIsNone(response)

    def test_resources_list(self):
        response = handle_request(
            {"jsonrpc": "2.0", "id": 5, "method": "resources/list"},
            self.skills, self.config
        )
        self.assertEqual(response["result"]["resources"], [])


class TestMCPClient(unittest.TestCase):
    def test_client_init(self):
        client = MCPClient("python3", ["-m", "skills.mcp.mcp_server"])
        self.assertEqual(client.command, "python3")
        self.assertIsNone(client.process)

    def test_client_id_counter(self):
        client = MCPClient("python3")
        id1 = client._next_id()
        id2 = client._next_id()
        self.assertEqual(id1, 1)
        self.assertEqual(id2, 2)


if __name__ == "__main__":
    unittest.main()
