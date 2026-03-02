import json
import time
import urllib.error
import urllib.request
from typing import Any, Callable, Dict


RETRYABLE_HTTP_CODES = {408, 429, 500, 502, 503, 504}


class AdapterExecutionError(RuntimeError):
    """Raised when provider adapter execution fails."""

    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


def post_json(url: str, headers: Dict[str, str], payload: Dict[str, Any], timeout: float) -> Dict[str, Any]:
    """POST JSON payload and return decoded JSON response."""
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url=url,
        data=body,
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="ignore")
        retryable = exc.code in RETRYABLE_HTTP_CODES
        raise AdapterExecutionError(
            f"HTTP {exc.code} from provider: {err_body[:300]}",
            retryable=retryable,
        ) from exc
    except urllib.error.URLError as exc:
        raise AdapterExecutionError(f"Network error calling provider: {exc}", retryable=True) from exc
    except TimeoutError as exc:
        raise AdapterExecutionError("Provider request timed out", retryable=True) from exc
    except json.JSONDecodeError as exc:
        raise AdapterExecutionError(f"Invalid JSON response: {exc}", retryable=False) from exc


def with_retry(fn: Callable[[], str], max_retries: int = 2, backoff_seconds: float = 0.4) -> str:
    """Run callable with retry/backoff for retryable adapter failures."""
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            return fn()
        except AdapterExecutionError as exc:
            last_error = exc
            if not exc.retryable or attempt >= max_retries:
                raise
            time.sleep(backoff_seconds * (attempt + 1))

    # Defensive, should never hit due to raise above.
    raise last_error or AdapterExecutionError("Unknown adapter error", retryable=False)
