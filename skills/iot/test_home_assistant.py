import json
import os
import tempfile
import unittest

from skills.iot.home_assistant import HomeAssistantManager, DynamicCredentialStore


class TestHomeAssistantManagerMock(unittest.TestCase):
    def setUp(self):
        for key in [
            "HOME_ASSISTANT_URL",
            "HA_BASE_URL",
            "HOME_ASSISTANT_ACCESS_TOKEN",
            "HA_ACCESS_TOKEN",
            "OPENPANGO_AGENT_CREDENTIALS_PATH",
        ]:
            os.environ.pop(key, None)

    def test_mock_mode_default(self):
        manager = HomeAssistantManager()
        self.assertTrue(manager._mock)

    def test_get_device_state_mock(self):
        manager = HomeAssistantManager()
        state = manager.get_device_state("light.living_room")
        self.assertEqual(state["state"], "off")
        self.assertTrue(state["mock"])

    def test_call_service_updates_mock_light_state(self):
        manager = HomeAssistantManager()
        manager.call_service("light", "turn_on", {"entity_id": "light.living_room"})
        state = manager.get_device_state("light.living_room")
        self.assertEqual(state["state"], "on")

        manager.call_service("light", "turn_off", {"entity_id": "light.living_room"})
        state = manager.get_device_state("light.living_room")
        self.assertEqual(state["state"], "off")

    def test_set_temperature_updates_attributes(self):
        manager = HomeAssistantManager()
        manager.call_service("climate", "set_temperature", {
            "entity_id": "climate.bedroom",
            "temperature": 26,
        })
        state = manager.get_device_state("climate.bedroom")
        self.assertEqual(state["attributes"]["temperature"], 26)


class TestCredentialStore(unittest.TestCase):
    def test_load_from_credentials_file(self):
        payload = {
            "agent_integrations": {
                "home_assistant": {
                    "base_url": "http://ha.local:8123",
                    "access_token": "abc123",
                }
            }
        }

        with tempfile.NamedTemporaryFile("w", delete=False) as f:
            json.dump(payload, f)
            tmp = f.name

        try:
            store = DynamicCredentialStore(credentials_path=tmp)
            creds = store.load_home_assistant()
            self.assertEqual(creds["base_url"], "http://ha.local:8123")
            self.assertEqual(creds["access_token"], "abc123")

            manager = HomeAssistantManager(credential_store=store)
            self.assertFalse(manager._mock)
            self.assertEqual(manager.base_url, "http://ha.local:8123")
        finally:
            os.unlink(tmp)


if __name__ == "__main__":
    unittest.main()
