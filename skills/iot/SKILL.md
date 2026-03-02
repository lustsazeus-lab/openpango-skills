---
name: iot
description: "Interact with smart home devices via Home Assistant. Control lights, thermostats, cameras, and more."
user-invocable: true
metadata: {"openclaw":{"emoji":"🏠","skillKey":"openpango-iot"}}
---

## Overview

This skill enables OpenPango agents to interact with the physical world through Home Assistant smart home instances. Agents can query device states, control devices (lights, switches, thermostats), and monitor security cameras.

## Setup

### Prerequisites

1. **Home Assistant Instance**: Running Home Assistant (local or cloud)
2. **Long-Lived Access Token**: Create in Home Assistant Profile > Long-Lived Access Tokens
3. **Environment Variables**: Set the following:

```bash
export HA_URL="http://homeassistant.local:8123"  # Your HA instance URL
export HA_TOKEN="your_long_lived_access_token"   # Your access token
```

### Security

- Tokens are stored in environment variables, not in code
- Use local IP for local instances (recommended)
- For remote access, use Home Assistant's cloud or a secure VPN

## Tools

### get_state

Get the current state of a specific entity.

```bash
python3 skills/iot/home_assistant.py get-state light.living_room
```

Returns:
```json
{
  "entity_id": "light.living_room",
  "state": "on",
  "attributes": {
    "brightness": 255,
    "color_temp": 370,
    "supported_color_modes": ["brightness", "color_temp"]
  },
  "last_changed": "2024-01-15T10:30:00.000000",
  "last_updated": "2024-01-15T10:30:00.000000"
}
```

### call_service

Call a Home Assistant service to control devices.

```bash
# Turn on a light
python3 skills/iot/home_assistant.py call-service light turn_on '{"entity_id": "light.living_room", "brightness": 128}'

# Turn off a light
python3 skills/iot/home_assistant.py call-service light turn_off '{"entity_id": "light.living_room"}'

# Set thermostat temperature
python3 skills/iot/home_assistant.py call-service climate set_temperature '{"entity_id": "climate.thermostat", "temperature": 72}'

# Lock a door
python3 skills/iot/home_assistant.py call-service lock lock '{"entity_id": "lock.front_door"}'
```

### list_entities

List all entities, optionally filtered by domain.

```bash
# List all lights
python3 skills/iot/home_assistant.py list-entities --domain light

# List all climate devices
python3 skills/iot/home_assistant.py list-entities --domain climate

# List all entities
python3 skills/iot/home_assistant.py list-entities
```

### get_states

Get all entity states at once.

```bash
python3 skills/iot/home_assistant.py get-states
```

### get_services

List all available services in Home Assistant.

```bash
python3 skills/iot/home_assistant.py get-services
```

### get_config

Get Home Assistant configuration.

```bash
python3 skills/iot/home_assistant.py get-config
```

## Common Use Cases

### Turn On Lights Before Arriving Home

```bash
python3 skills/iot/home_assistant.py call-service light turn_on '{"entity_id": "light.entrance", "brightness": 255}'
```

### Check Thermostat Temperature

```bash
python3 skills/iot/home_assistant.py get-state climate.thermostat
```

### Arm Security System

```bash
python3 skills/iot/home_assistant.py call-service alarm_control_panel arm_away '{"entity_id": "alarm_control_panel.home"}'
```

### View Camera Feed

Note: This returns the camera entity state; actual stream URLs require additional configuration.

```bash
python3 skills/iot/home_assistant.py get-state camera.front_door
```

## Error Handling

The tool returns errors as JSON:

```json
{
  "error": "HA_TOKEN environment variable not set. Please configure your Home Assistant access token."
}
```

Or HTTP errors:
```json
{
  "error": "Home Assistant API error (404): Entity not found"
}
```
