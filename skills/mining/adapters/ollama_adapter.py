from .base import AdapterExecutionError, post_json, with_retry


OLLAMA_ENDPOINT = "http://localhost:11434/api/generate"


def execute(prompt: str, model: str, api_key: str, timeout: float = 30.0, max_retries: int = 2) -> str:
    """Execute prompt against local Ollama daemon.

    `api_key` is accepted for interface consistency but unused.
    """

    def _call() -> str:
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        data = post_json(OLLAMA_ENDPOINT, headers={}, payload=payload, timeout=timeout)
        response_text = data.get("response") if isinstance(data, dict) else None
        if not response_text:
            raise AdapterExecutionError("Unexpected Ollama response schema", retryable=False)
        return response_text

    return with_retry(_call, max_retries=max_retries)
