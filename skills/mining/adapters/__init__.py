from typing import Callable, Dict

from .anthropic_adapter import execute as execute_anthropic
from .base import AdapterExecutionError
from .google_adapter import execute as execute_google
from .ollama_adapter import execute as execute_ollama
from .openai_adapter import execute as execute_openai


AdapterFn = Callable[[str, str, str, float, int], str]


ADAPTERS: Dict[str, AdapterFn] = {
    "openai": execute_openai,
    "anthropic": execute_anthropic,
    "google": execute_google,
    "ollama": execute_ollama,
}


def infer_provider(model: str) -> str:
    """Infer provider from model naming conventions."""
    model_lower = (model or "").lower()

    if any(model_lower.startswith(prefix) for prefix in ("gpt", "o1", "o3", "o4", "text-embedding")):
        return "openai"
    if "claude" in model_lower:
        return "anthropic"
    if "gemini" in model_lower or "palm" in model_lower:
        return "google"
    if any(model_lower.startswith(prefix) for prefix in ("llama", "mistral", "qwen", "deepseek")):
        return "ollama"
    return "openai"


def execute_inference(
    provider: str,
    prompt: str,
    model: str,
    api_key: str,
    timeout: float = 30.0,
    max_retries: int = 2,
) -> str:
    """Dispatch to provider adapter."""
    adapter = ADAPTERS.get((provider or "").lower())
    if adapter is None:
        raise AdapterExecutionError(f"Unsupported provider: {provider}", retryable=False)

    return adapter(prompt, model, api_key, timeout, max_retries)
