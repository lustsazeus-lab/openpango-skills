import unittest
from unittest.mock import patch

from skills.mining.adapters import execute_inference, infer_provider
from skills.mining.adapters.base import AdapterExecutionError


class TestMiningAdapters(unittest.TestCase):

    @patch("skills.mining.adapters.openai_adapter.post_json")
    def test_openai_adapter_execute(self, mock_post_json):
        mock_post_json.return_value = {
            "choices": [{"message": {"content": "openai ok"}}]
        }
        out = execute_inference("openai", "hello", "gpt-4o", "sk-openai")
        self.assertEqual(out, "openai ok")

    @patch("skills.mining.adapters.anthropic_adapter.post_json")
    def test_anthropic_adapter_execute(self, mock_post_json):
        mock_post_json.return_value = {
            "content": [
                {"type": "text", "text": "anthropic"},
                {"type": "text", "text": " ok"},
            ]
        }
        out = execute_inference("anthropic", "hello", "claude-3-5-sonnet", "sk-ant")
        self.assertEqual(out, "anthropic ok")

    @patch("skills.mining.adapters.google_adapter.post_json")
    def test_google_adapter_execute(self, mock_post_json):
        mock_post_json.return_value = {
            "candidates": [
                {"content": {"parts": [{"text": "gemini ok"}]}}
            ]
        }
        out = execute_inference("google", "hello", "gemini-1.5-pro", "google-key")
        self.assertEqual(out, "gemini ok")

    @patch("skills.mining.adapters.ollama_adapter.post_json")
    def test_ollama_adapter_execute(self, mock_post_json):
        mock_post_json.return_value = {"response": "ollama ok"}
        out = execute_inference("ollama", "hello", "llama3", "unused")
        self.assertEqual(out, "ollama ok")

    @patch("skills.mining.adapters.openai_adapter.post_json")
    def test_retry_logic_on_transient_failure(self, mock_post_json):
        mock_post_json.side_effect = [
            AdapterExecutionError("temporary", retryable=True),
            {"choices": [{"message": {"content": "recovered"}}]},
        ]
        out = execute_inference("openai", "hello", "gpt-4o", "sk-openai", max_retries=2)
        self.assertEqual(out, "recovered")
        self.assertEqual(mock_post_json.call_count, 2)

    def test_infer_provider(self):
        self.assertEqual(infer_provider("gpt-4o"), "openai")
        self.assertEqual(infer_provider("claude-3-opus"), "anthropic")
        self.assertEqual(infer_provider("gemini-1.5-pro"), "google")
        self.assertEqual(infer_provider("llama3"), "ollama")


if __name__ == "__main__":
    unittest.main()
