import urllib.parse

from .base import AdapterExecutionError, post_json, with_retry


DEFAULT_GEMINI_MODEL = "gemini-1.5-pro"


def execute(prompt: str, model: str, api_key: str, timeout: float = 30.0, max_retries: int = 2) -> str:
    """Execute prompt against Google Gemini generateContent API."""
    if not api_key:
        raise AdapterExecutionError("Google API key is required", retryable=False)

    def _call() -> str:
        resolved_model = model or DEFAULT_GEMINI_MODEL
        encoded_model = urllib.parse.quote(resolved_model, safe="")
        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{encoded_model}:generateContent?key={urllib.parse.quote(api_key, safe='')}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
        }
        data = post_json(endpoint, headers={}, payload=payload, timeout=timeout)
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AdapterExecutionError("Unexpected Google Gemini response schema", retryable=False) from exc

    return with_retry(_call, max_retries=max_retries)
