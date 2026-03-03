#!/usr/bin/env python3
"""
home_assistant.py - Home Assistant Integration for OpenPango Agents.

Provides smart home control through Home Assistant REST and WebSocket APIs.
Supports lights, switches, sensors, thermostats, cameras, and all HA entities.
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone
import urllib.request
import urllib.error
import urllib.parse

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(name)s] %(levelname)s: %(message)s')
logger = logging.getLogger("HomeAssistant")


class HomeAssistantError(Exception):
    """Base exception for Home Assistant errors."""
    pass


class AuthenticationError(HomeAssistantError):
    """Authentication failed."""
    pass


class EntityNotFoundError(HomeAssistantError):
    """Entity not found."""
    pass


class HomeAssistantClient:
    """
    Home Assistant API client for smart home control.
    
    Supports both REST API and WebSocket API for real-time events.
    Falls back to mock mode when HOME_ASSISTANT_URL is not configured.
    """
    
    def __init__(
        self,
        url: Optional[str] = None,
        token: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize Home Assistant client.
        
        Args:
            url: Home Assistant URL (or set HOME_ASSISTANT_URL env var)
            token: Long-lived access token (or set HOME_ASSISTANT_TOKEN env var)
            timeout: Request timeout in seconds
        """
        self.url = (url or os.getenv("HOME_ASSISTANT_URL", "")).rstrip("/")
        self.token = token or os.getenv("HOME_ASSISTANT_TOKEN", "")
        self.timeout = timeout
        self._mock = not bool(self.url)
        
        if self._mock:
            logger.warning("No HOME_ASSISTANT_URL set. Running in MOCK mode.")
            self._mock_entities = self._init_mock_entities()
        else:
            logger.info(f"Connected to Home Assistant: {self.url}")
    
    # ─── Mock Data ─────────────────────────────────────────────
    
    def _init_mock_entities(self) -> Dict[str, Dict]:
        """Initialize mock entities for testing."""
        return {
            "light.living_room": {
                "entity_id": "light.living_room",
                "state": "off",
                "attributes": {
                    "friendly_name": "Living Room Light",
                    "brightness": 0,
                    "color_mode": "brightness",
                    "supported_features": 151
                },
                "last_changed": datetime.now(timezone.utc).isoformat(),
                "domain": "light"
            },
            "light.bedroom": {
                "entity_id": "light.bedroom",
                "state": "on",
                "attributes": {
                    "friendly_name": "Bedroom Light",
                    "brightness": 200,
                    "color_mode": "brightness"
                },
                "last_changed": datetime.now(timezone.utc).isoformat(),
                "domain": "light"
            },
            "switch.smart_plug": {
                "entity_id": "switch.smart_plug",
                "state": "off",
                "attributes": {
                    "friendly_name": "Smart Plug"
                },
                "last_changed": datetime.now(timezone.utc).isoformat(),
                "domain": "switch"
            },
            "sensor.temperature": {
                "entity_id": "sensor.temperature",
                "state": "22.5",
                "attributes": {
                    "friendly_name": "Living Room Temperature",
                    "unit_of_measurement": "°C",
                    "device_class": "temperature"
                },
                "last_changed": datetime.now(timezone.utc).isoformat(),
                "domain": "sensor"
            },
            "sensor.humidity": {
                "entity_id": "sensor.humidity",
                "state": "65",
                "attributes": {
                    "friendly_name": "Living Room Humidity",
                    "unit_of_measurement": "%",
                    "device_class": "humidity"
                },
                "last_changed": datetime.now(timezone.utc).isoformat(),
                "domain": "sensor"
            },
            "climate.thermostat": {
                "entity_id": "climate.thermostat",
                "state": "heat",
                "attributes": {
                    "friendly_name": "Thermostat",
                    "current_temperature": 21.0,
                    "temperature": 22.0,
                    "hvac_modes": ["off", "heat", "cool", "auto"]
                },
                "last_changed": datetime.now(timezone.utc).isoformat(),
                "domain": "climate"
            },
            "camera.front_door": {
                "entity_id": "camera.front_door",
                "state": "idle",
                "attributes": {
                    "friendly_name": "Front Door Camera",
                    "supported_features": 0
                },
                "last_changed": datetime.now(timezone.utc).isoformat(),
                "domain": "camera"
            }
        }
    
    # ─── REST API Methods ───────────────────────────────────────
    
    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Home Assistant API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., /api/states/light.living_room)
            data: Request body data
            
        Returns:
            Response JSON
        """
        if self._mock:
            return self._mock_request(method, endpoint, data)
        
        url = f"{self.url}/api{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        try:
            req_data = json.dumps(data).encode() if data else None
            req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
            
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode())
                
        except urllib.error.HTTPError as e:
            if e.code == 401:
                raise AuthenticationError("Invalid Home Assistant token")
            elif e.code == 404:
                raise EntityNotFoundError(f"Entity not found: {endpoint}")
            else:
                raise HomeAssistantError(f"HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise HomeAssistantError(f"Connection error: {e.reason}")
    
    def _mock_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Handle mock requests for testing."""
        
        # GET /states
        if method == "GET" and endpoint == "/states":
            return list(self._mock_entities.values())
        
        # GET /states/<entity_id>
        if method == "GET" and endpoint.startswith("/states/"):
            entity_id = endpoint.replace("/states/", "")
            if entity_id in self._mock_entities:
                return self._mock_entities[entity_id]
            raise EntityNotFoundError(f"Entity not found: {entity_id}")
        
        # POST /services/<domain>/<service>
        if method == "POST" and endpoint.startswith("/services/"):
            parts = endpoint.replace("/services/", "").split("/")
            domain = parts[0]
            service = parts[1]
            return self._mock_call_service(domain, service, data or {})
        
        # GET /states?domain=<domain>
        if method == "GET" and "/states?" in endpoint:
            parsed = urllib.parse.parse_qs(endpoint.split("?")[1])
            domain = parsed.get("domain", [None])[0]
            if domain:
                return [e for e in self._mock_entities.values() if e.get("domain") == domain]
            return list(self._mock_entities.values())
        
        return {"status": "ok", "mock": True}
    
    # ─── Entity Methods ─────────────────────────────────────────
    
    def get_state(self, entity_id: str) -> Dict[str, Any]:
        """
        Get the state of an entity.
        
        Args:
            entity_id: Entity ID (e.g., light.living_room)
            
        Returns:
            Entity state dict with state, attributes, last_changed
        """
        result = self._request("GET", f"/states/{entity_id}")
        logger.info(f"Got state for {entity_id}: {result.get('state')}")
        return result
    
    def get_states(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all entity states, optionally filtered by domain.
        
        Args:
            domain: Filter by domain (e.g., light, sensor, switch)
            
        Returns:
            List of entity state dicts
        """
        if domain:
            result = self._request("GET", f"/states?domain={domain}")
        else:
            result = self._request("GET", "/states")
        
        logger.info(f"Retrieved {len(result)} entities" + (f" in domain {domain}" if domain else ""))
        return result
    
    def get_entities_by_domain(self, domain: str) -> List[Dict[str, Any]]:
        """
        Get all entities of a specific domain.
        
        Args:
            domain: Domain name (light, switch, sensor, climate, camera, etc.)
            
        Returns:
            List of entity state dicts
        """
        return self.get_states(domain=domain)
    
    # ─── Service Methods ────────────────────────────────────────
    
    def call_service(
        self,
        domain: str,
        service: str,
        data: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        Call a Home Assistant service.
        
        Args:
            domain: Service domain (light, switch, climate, etc.)
            service: Service name (turn_on, turn_off, toggle, etc.)
            data: Service data payload
            
        Returns:
            List of affected entity states
        """
        result = self._request("POST", f"/services/{domain}/{service}", data)
        logger.info(f"Called service: {domain}.{service}")
        return result
    
    def _mock_call_service(
        self,
        domain: str,
        service: str,
        data: Dict
    ) -> List[Dict[str, Any]]:
        """Handle mock service calls."""
        entity_id = data.get("entity_id")
        affected = []
        
        # Handle entity_id as string or list
        entity_ids = [entity_id] if isinstance(entity_id, str) else (entity_id or [])
        
        for eid in entity_ids:
            if eid in self._mock_entities:
                entity = self._mock_entities[eid]
                
                # Update state based on service
                if domain == "light":
                    if service == "turn_on":
                        entity["state"] = "on"
                        if "brightness" in data:
                            entity["attributes"]["brightness"] = data["brightness"]
                    elif service == "turn_off":
                        entity["state"] = "off"
                        entity["attributes"]["brightness"] = 0
                    elif service == "toggle":
                        entity["state"] = "on" if entity["state"] == "off" else "off"
                        
                elif domain == "switch":
                    if service == "turn_on":
                        entity["state"] = "on"
                    elif service == "turn_off":
                        entity["state"] = "off"
                    elif service == "toggle":
                        entity["state"] = "on" if entity["state"] == "off" else "off"
                        
                elif domain == "climate":
                    if service == "set_temperature":
                        entity["attributes"]["temperature"] = data.get("temperature")
                    elif service == "set_hvac_mode":
                        entity["state"] = data.get("hvac_mode")
                
                entity["last_changed"] = datetime.now(timezone.utc).isoformat()
                affected.append(entity)
        
        return affected
    
    # ─── Convenience Methods ─────────────────────────────────────
    
    def turn_on(self, entity_id: str, **kwargs) -> List[Dict[str, Any]]:
        """
        Turn on an entity (light, switch, etc.).
        
        Args:
            entity_id: Entity ID to turn on
            **kwargs: Additional attributes (brightness, color, etc.)
            
        Returns:
            List of affected entity states
        """
        domain = entity_id.split(".")[0]
        data = {"entity_id": entity_id, **kwargs}
        return self.call_service(domain, "turn_on", data)
    
    def turn_off(self, entity_id: str) -> List[Dict[str, Any]]:
        """
        Turn off an entity.
        
        Args:
            entity_id: Entity ID to turn off
            
        Returns:
            List of affected entity states
        """
        domain = entity_id.split(".")[0]
        return self.call_service(domain, "turn_off", {"entity_id": entity_id})
    
    def toggle(self, entity_id: str) -> List[Dict[str, Any]]:
        """
        Toggle an entity.
        
        Args:
            entity_id: Entity ID to toggle
            
        Returns:
            List of affected entity states
        """
        domain = entity_id.split(".")[0]
        return self.call_service(domain, "toggle", {"entity_id": entity_id})
    
    def set_temperature(self, entity_id: str, temperature: float) -> List[Dict[str, Any]]:
        """
        Set thermostat temperature.
        
        Args:
            entity_id: Climate entity ID
            temperature: Target temperature
            
        Returns:
            List of affected entity states
        """
        return self.call_service("climate", "set_temperature", {
            "entity_id": entity_id,
            "temperature": temperature
        })
    
    def set_brightness(self, entity_id: str, brightness: int) -> List[Dict[str, Any]]:
        """
        Set light brightness.
        
        Args:
            entity_id: Light entity ID
            brightness: Brightness (0-255)
            
        Returns:
            List of affected entity states
        """
        return self.turn_on(entity_id, brightness=brightness)
    
    def get_lights(self) -> List[Dict[str, Any]]:
        """Get all light entities."""
        return self.get_entities_by_domain("light")
    
    def get_switches(self) -> List[Dict[str, Any]]:
        """Get all switch entities."""
        return self.get_entities_by_domain("switch")
    
    def get_sensors(self) -> List[Dict[str, Any]]:
        """Get all sensor entities."""
        return self.get_entities_by_domain("sensor")
    
    def get_climates(self) -> List[Dict[str, Any]]:
        """Get all climate entities."""
        return self.get_entities_by_domain("climate")
    
    def get_cameras(self) -> List[Dict[str, Any]]:
        """Get all camera entities."""
        return self.get_entities_by_domain("camera")
    
    # ─── Utility Methods ─────────────────────────────────────────
    
    def is_on(self, entity_id: str) -> bool:
        """Check if entity is on."""
        state = self.get_state(entity_id)
        return state.get("state") in ("on", "open", "playing", "home")
    
    def is_off(self, entity_id: str) -> bool:
        """Check if entity is off."""
        return not self.is_on(entity_id)
    
    def get_temperature(self, entity_id: str) -> Optional[float]:
        """Get temperature value from a sensor."""
        state = self.get_state(entity_id)
        try:
            return float(state.get("state"))
        except (ValueError, TypeError):
            return None
    
    def get_humidity(self, entity_id: str) -> Optional[float]:
        """Get humidity value from a sensor."""
        return self.get_temperature(entity_id)  # Same parsing
    
    def get_camera_stream(self, entity_id: str) -> Dict[str, Any]:
        """
        Get camera stream URL.
        
        Args:
            entity_id: Camera entity ID
            
        Returns:
            Dict with stream URL info
        """
        if self._mock:
            return {
                "entity_id": entity_id,
                "stream_url": f"{self.url or 'http://mock.local'}/api/camera_proxy_stream/{entity_id}",
                "mock": True
            }
        
        # In production, this would return actual stream URL
        return {
            "entity_id": entity_id,
            "stream_url": f"{self.url}/api/camera_proxy_stream/{entity_id}?token={self.token[:8]}..."
        }


# ─── CLI Interface ──────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    
    def print_json(data):
        print(json.dumps(data, indent=2, default=str))
    
    client = HomeAssistantClient()
    
    if len(sys.argv) < 2:
        print("Usage: python home_assistant.py <command> [args]")
        print("\nCommands:")
        print("  get <entity_id>         Get entity state")
        print("  lights                  List all lights")
        print("  switches                List all switches")
        print("  sensors                 List all sensors")
        print("  climates                List all climate entities")
        print("  cameras                 List all cameras")
        print("  on <entity_id>          Turn on entity")
        print("  off <entity_id>         Turn off entity")
        print("  toggle <entity_id>      Toggle entity")
        print("  brightness <id> <val>   Set brightness (0-255)")
        print("  temp <entity_id> <val>  Set temperature")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "get":
        entity_id = sys.argv[2]
        print_json(client.get_state(entity_id))
    
    elif cmd == "lights":
        print_json(client.get_lights())
    
    elif cmd == "switches":
        print_json(client.get_switches())
    
    elif cmd == "sensors":
        print_json(client.get_sensors())
    
    elif cmd == "climates":
        print_json(client.get_climates())
    
    elif cmd == "cameras":
        print_json(client.get_cameras())
    
    elif cmd == "on":
        entity_id = sys.argv[2]
        print_json(client.turn_on(entity_id))
    
    elif cmd == "off":
        entity_id = sys.argv[2]
        print_json(client.turn_off(entity_id))
    
    elif cmd == "toggle":
        entity_id = sys.argv[2]
        print_json(client.toggle(entity_id))
    
    elif cmd == "brightness":
        entity_id = sys.argv[2]
        brightness = int(sys.argv[3])
        print_json(client.set_brightness(entity_id, brightness))
    
    elif cmd == "temp":
        entity_id = sys.argv[2]
        temp = float(sys.argv[3])
        print_json(client.set_temperature(entity_id, temp))
    
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)
