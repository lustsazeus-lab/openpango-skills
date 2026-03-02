from .base import AdapterExecutionError, post_json, with_retry


ANTHROPIC_VERSION = "2023-06-01"


def execute(prompt: str, model: str, api_key: str, timeout: float = 30.0, max_retries: int = 2) -> str:
    """Execute prompt against Anthropic Messages API."""
    if not api_key:
        raise AdapterExecutionError("Anthropic API key is required", retryable=False)

    def _call() -> str:
        payload = {
            "model": model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}],
        }
        data = post_json(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": ANTHROPIC_VERSION,
            },
            payload=payload,
            timeout=timeout,
        )
        try:
            content = data["content"]
            texts = [chunk.get("text", "") for chunk in content if isinstance(chunk, dict)]
            response_text = "".join([t for t in texts if t])
            if not response_text:
                raise KeyError("No text content found")
            return response_text
        except (KeyError, TypeError, AttributeError) as exc:
            raise AdapterExecutionError("Unexpected Anthropic response schema", retryable=False) from exc

    return with_retry(_call, max_retries=max_retries)
