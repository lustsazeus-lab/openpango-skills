---
name: iot
description: "Home Assistant integration for smart home control. Control lights, thermostats, security cameras, and all Home Assistant entities."
version: "1.0.0"
user-invocable: true
metadata:
  capabilities:
    - iot/home_assistant
    - iot/device_control
    - iot/sensors
    - iot/automation
  author: "XiaoWen (OpenPango Contributor)"
  license: "MIT"
---

# IoT & Home Assistant Skill

Enables OpenPango agents to interact with the physical world through smart home devices. Integrates with Home Assistant instances via REST and WebSocket APIs.

## Features

- **Device State**: Query any entity's state (lights, sensors, switches, etc.)
- **Service Calls**: Control devices via Home Assistant services
- **Real-time Events**: Subscribe to state changes via WebSocket
- **Secure Credentials**: API tokens stored via dynamic agent credentials

## Usage

```python
from skills.iot.home_assistant import HomeAssistantClient

# Initialize client
ha = HomeAssistantClient(
    url="http://homeassistant.local:8123",
    token="your-long-lived-access-token"
)

# Get device state
state = ha.get_state("light.living_room")
print(f"State: {state['state']}, Brightness: {state['attributes'].get('brightness')}")

# Turn on light
ha.call_service("light", "turn_on", {"entity_id": "light.living_room", "brightness": 255})

# Get all lights
lights = ha.get_entities_by_domain("light")
for light in lights:
    print(f"{light['entity_id']}: {light['state']}")
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `HOME_ASSISTANT_URL` | Home Assistant URL (e.g., http://homeassistant.local:8123) |
| `HOME_ASSISTANT_TOKEN` | Long-lived access token |

## Security

- Tokens are never logged or exposed in error messages
- All API calls use HTTPS when available
- Supports local and remote Home Assistant instances
