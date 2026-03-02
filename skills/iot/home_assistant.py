#!/usr/bin/env python3
"""
home_assistant.py - OpenPango IoT skill for Home Assistant integration.

Features:
- Read entity state: get_device_state(entity_id)
- Invoke services: call_service(domain, service, payload)
- Mock mode fallback when credentials are unavailable
- Dynamic credential loading from env or credentials file
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger("HomeAssistantSkill")


@dataclass
class HomeAssistantConfig:
    base_url: str = ""
    access_token: str = ""
    timeout_seconds: float = 10.0


class DynamicCredentialStore:
    """
    Minimal credential loader aligned with a dynamic agent-credentials flow.

    Resolution order:
      1) Explicit environment variables
      2) OPENPANGO_AGENT_CREDENTIALS_PATH JSON file

    Expected JSON shape (flexible):
    {
      "home_assistant": {
        "base_url": "http://ha.local:8123",
        "access_token": "..."
      }
    }
    or
    {
      "agent_integrations": {
        "home_assistant": {
          "base_url": "...",
          "access_token": "..."
        }
      }
    }
    """

    def __init__(self, credentials_path: Optional[str] = None):
        self.credentials_path = (
            credentials_path
            or os.getenv("OPENPANGO_AGENT_CREDENTIALS_PATH")
            or os.path.expanduser("~/.openclaw/workspace/.agent_credentials.json")
        )

    def load_home_assistant(self) -> Dict[str, str]:
        # Env-first override for secure runtime injection.
        env_base = os.getenv("HOME_ASSISTANT_URL") or os.getenv("HA_BASE_URL")
        env_token = os.getenv("HOME_ASSISTANT_ACCESS_TOKEN") or os.getenv("HA_ACCESS_TOKEN")
        if env_base and env_token:
            return {"base_url": env_base, "access_token": env_token}

        path = Path(self.credentials_path)
        if not path.exists():
            return {}

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - defensive path
            logger.warning("Failed to parse credentials file at %s: %s", path, exc)
            return {}

        direct = data.get("home_assistant") if isinstance(data, dict) else None
        if isinstance(direct, dict):
            return {
                "base_url": str(direct.get("base_url", "")),
                "access_token": str(direct.get("access_token", "")),
            }

        nested = (
            data.get("agent_integrations", {}).get("home_assistant", {})
            if isinstance(data, dict)
            else {}
        )
        if isinstance(nested, dict):
            return {
                "base_url": str(nested.get("base_url", "")),
                "access_token": str(nested.get("access_token", "")),
            }

        return {}


class HomeAssistantManager:
    """Home Assistant integration manager with live + mock execution paths."""

    def __init__(
        self,
        config: Optional[HomeAssistantConfig] = None,
        credential_store: Optional[DynamicCredentialStore] = None,
    ):
        self._credential_store = credential_store or DynamicCredentialStore()
        cred = self._credential_store.load_home_assistant()

        cfg = config or HomeAssistantConfig()
        self.base_url = (cfg.base_url or cred.get("base_url") or "").rstrip("/")
        self.access_token = cfg.access_token or cred.get("access_token") or ""
        self.timeout_seconds = cfg.timeout_seconds

        self._mock = not (self.base_url and self.access_token)
        self._mock_states: Dict[str, Dict[str, Any]] = {
            "light.living_room": {
                "entity_id": "light.living_room",
                "state": "off",
                "attributes": {"friendly_name": "Living Room Light"},
                "last_changed": datetime.now(timezone.utc).isoformat(),
            },
            "climate.bedroom": {
                "entity_id": "climate.bedroom",
                "state": "cool",
                "attributes": {"temperature": 24, "friendly_name": "Bedroom Thermostat"},
                "last_changed": datetime.now(timezone.utc).isoformat(),
            },
        }

        if self._mock:
            logger.warning("HomeAssistantManager running in MOCK mode (credentials unavailable).")

    def get_device_state(self, entity_id: str) -> Dict[str, Any]:
        """Return current state for an entity id (e.g. light.kitchen)."""
        if self._mock:
            state = self._mock_states.get(entity_id)
            if not state:
                return {
                    "error": f"Entity not found: {entity_id}",
                    "entity_id": entity_id,
                    "mock": True,
                }
            return {**state, "mock": True}

        encoded = urllib.parse.quote(entity_id, safe="")
        return self._request("GET", f"/api/states/{encoded}")

    def call_service(self, domain: str, service: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Invoke a Home Assistant service call with JSON payload."""
        payload = payload or {}

        if self._mock:
            entity_id = payload.get("entity_id")
            now = datetime.now(timezone.utc).isoformat()

            if entity_id and entity_id in self._mock_states:
                if domain == "light" and service == "turn_on":
                    self._mock_states[entity_id]["state"] = "on"
                elif domain == "light" and service == "turn_off":
                    self._mock_states[entity_id]["state"] = "off"
                elif domain == "climate" and service == "set_temperature":
                    temp = payload.get("temperature")
                    if temp is not None:
                        self._mock_states[entity_id]["attributes"]["temperature"] = temp
                self._mock_states[entity_id]["last_changed"] = now

            return {
                "status": "called",
                "domain": domain,
                "service": service,
                "payload": payload,
                "timestamp": now,
                "mock": True,
            }

        return self._request("POST", f"/api/services/{domain}/{service}", payload)

    def set_mock_state(self, entity_id: str, state: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Testing helper to seed/update mock entities."""
        self._mock_states[entity_id] = {
            "entity_id": entity_id,
            "state": state,
            "attributes": attributes or {},
            "last_changed": datetime.now(timezone.utc).isoformat(),
        }

    def _request(self, method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self._mock:
            return {"error": "Request unavailable in mock mode", "mock": True}

        url = f"{self.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url=url, method=method, data=data, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                raw = resp.read().decode("utf-8")
                if not raw:
                    return {"status": "ok"}
                parsed = json.loads(raw)
                return parsed if isinstance(parsed, dict) else {"result": parsed}
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="ignore")
            return {
                "error": "http_error",
                "status_code": exc.code,
                "detail": detail,
            }
        except Exception as exc:
            return {
                "error": "request_failed",
                "detail": str(exc),
            }


def _parse_payload(raw: str) -> Dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
        raise ValueError("payload must be a JSON object")
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON payload: {exc}") from exc


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Home Assistant Skill Manager")
    sub = parser.add_subparsers(dest="cmd", required=True)

    state_cmd = sub.add_parser("state", help="Get entity state")
    state_cmd.add_argument("entity_id", help="Entity id, e.g. light.kitchen")

    call_cmd = sub.add_parser("call", help="Call Home Assistant service")
    call_cmd.add_argument("domain", help="Service domain, e.g. light")
    call_cmd.add_argument("service", help="Service name, e.g. turn_on")
    call_cmd.add_argument("--payload", default="{}", help="JSON payload")

    args = parser.parse_args()
    manager = HomeAssistantManager()

    if args.cmd == "state":
        result = manager.get_device_state(args.entity_id)
    else:
        result = manager.call_service(args.domain, args.service, _parse_payload(args.payload))

    print(json.dumps(result, indent=2))
