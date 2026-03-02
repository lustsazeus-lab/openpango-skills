---
name: iot-home
description: "Home Assistant integration for smart-home device state and service control."
user-invocable: true
metadata: {"openclaw":{"emoji":"🏠","skillKey":"openpango-iot-home"}}
---

## Overview

The `iot-home` skill gives agents a safe interface to Home Assistant.

### Tools
- `get_device_state(entity_id)`
- `call_service(domain, service, payload)`

### Authentication

Credential resolution order:
1. `HOME_ASSISTANT_URL` + `HOME_ASSISTANT_ACCESS_TOKEN`
2. `OPENPANGO_AGENT_CREDENTIALS_PATH` JSON file (`home_assistant` or `agent_integrations.home_assistant`)

If credentials are unavailable, the skill runs in **mock mode** for local testing.

## CLI Usage

```bash
python3 skills/iot/home_assistant.py state light.living_room
python3 skills/iot/home_assistant.py call light turn_on --payload '{"entity_id":"light.living_room"}'
```
