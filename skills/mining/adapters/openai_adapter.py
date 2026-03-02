from .base import AdapterExecutionError, post_json, with_retry


def execute(prompt: str, model: str, api_key: str, timeout: float = 30.0, max_retries: int = 2) -> str:
    """Execute prompt against OpenAI Chat Completions API."""
    if not api_key:
        raise AdapterExecutionError("OpenAI API key is required", retryable=False)

    def _call() -> str:
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        data = post_json(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            payload=payload,
            timeout=timeout,
        )
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AdapterExecutionError("Unexpected OpenAI response schema", retryable=False) from exc

    return with_retry(_call, max_retries=max_retries)
