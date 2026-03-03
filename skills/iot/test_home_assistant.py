#!/usr/bin/env python3
"""
test_home_assistant.py - Tests for Home Assistant integration skill.
"""

import os
import sys
import json
import unittest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from skills.iot.home_assistant import (
    HomeAssistantClient,
    HomeAssistantError,
    AuthenticationError,
    EntityNotFoundError
)


class TestHomeAssistantClient(unittest.TestCase):
    """Test Home Assistant client in mock mode."""
    
    def setUp(self):
        """Set up test client in mock mode."""
        self.client = HomeAssistantClient()
    
    def test_mock_mode(self):
        """Test that client starts in mock mode without URL."""
        self.assertTrue(self.client._mock)
    
    def test_get_state(self):
        """Test getting entity state."""
        state = self.client.get_state("light.living_room")
        
        self.assertEqual(state["entity_id"], "light.living_room")
        self.assertIn("state", state)
        self.assertIn("attributes", state)
        self.assertIn("friendly_name", state["attributes"])
    
    def test_get_state_not_found(self):
        """Test getting non-existent entity raises error."""
        with self.assertRaises(EntityNotFoundError):
            self.client.get_state("light.nonexistent")
    
    def test_get_states(self):
        """Test getting all entity states."""
        states = self.client.get_states()
        
        self.assertIsInstance(states, list)
        self.assertGreater(len(states), 0)
    
    def test_get_entities_by_domain(self):
        """Test getting entities by domain."""
        lights = self.client.get_entities_by_domain("light")
        
        self.assertIsInstance(lights, list)
        for light in lights:
            self.assertTrue(light["entity_id"].startswith("light."))
    
    def test_get_lights(self):
        """Test getting all lights."""
        lights = self.client.get_lights()
        
        self.assertIsInstance(lights, list)
        entity_ids = [l["entity_id"] for l in lights]
        self.assertIn("light.living_room", entity_ids)
        self.assertIn("light.bedroom", entity_ids)
    
    def test_get_switches(self):
        """Test getting all switches."""
        switches = self.client.get_switches()
        
        self.assertIsInstance(switches, list)
        entity_ids = [s["entity_id"] for s in switches]
        self.assertIn("switch.smart_plug", entity_ids)
    
    def test_get_sensors(self):
        """Test getting all sensors."""
        sensors = self.client.get_sensors()
        
        self.assertIsInstance(sensors, list)
        entity_ids = [s["entity_id"] for s in sensors]
        self.assertIn("sensor.temperature", entity_ids)
        self.assertIn("sensor.humidity", entity_ids)
    
    def test_get_climates(self):
        """Test getting all climate entities."""
        climates = self.client.get_climates()
        
        self.assertIsInstance(climates, list)
        entity_ids = [c["entity_id"] for c in climates]
        self.assertIn("climate.thermostat", entity_ids)
    
    def test_get_cameras(self):
        """Test getting all cameras."""
        cameras = self.client.get_cameras()
        
        self.assertIsInstance(cameras, list)
        entity_ids = [c["entity_id"] for c in cameras]
        self.assertIn("camera.front_door", entity_ids)
    
    def test_turn_on_light(self):
        """Test turning on a light."""
        result = self.client.turn_on("light.living_room")
        
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["state"], "on")
    
    def test_turn_off_light(self):
        """Test turning off a light."""
        # First turn on
        self.client.turn_on("light.living_room")
        
        # Then turn off
        result = self.client.turn_off("light.living_room")
        
        self.assertEqual(result[0]["state"], "off")
        self.assertEqual(result[0]["attributes"]["brightness"], 0)
    
    def test_toggle_light(self):
        """Test toggling a light."""
        # Get initial state
        initial = self.client.get_state("light.living_room")
        initial_state = initial["state"]
        
        # Toggle
        result = self.client.toggle("light.living_room")
        
        # State should be opposite
        expected = "off" if initial_state == "on" else "on"
        self.assertEqual(result[0]["state"], expected)
    
    def test_set_brightness(self):
        """Test setting light brightness."""
        result = self.client.set_brightness("light.living_room", 200)
        
        self.assertEqual(result[0]["state"], "on")
        self.assertEqual(result[0]["attributes"]["brightness"], 200)
    
    def test_set_temperature(self):
        """Test setting thermostat temperature."""
        result = self.client.set_temperature("climate.thermostat", 23.5)
        
        self.assertEqual(result[0]["attributes"]["temperature"], 23.5)
    
    def test_is_on(self):
        """Test checking if entity is on."""
        # Turn on first
        self.client.turn_on("light.living_room")
        
        self.assertTrue(self.client.is_on("light.living_room"))
        self.assertFalse(self.client.is_off("light.living_room"))
    
    def test_is_off(self):
        """Test checking if entity is off."""
        # Turn off first
        self.client.turn_off("light.living_room")
        
        self.assertTrue(self.client.is_off("light.living_room"))
        self.assertFalse(self.client.is_on("light.living_room"))
    
    def test_get_temperature_sensor(self):
        """Test getting temperature from sensor."""
        temp = self.client.get_temperature("sensor.temperature")
        
        self.assertIsInstance(temp, float)
        self.assertEqual(temp, 22.5)
    
    def test_get_humidity_sensor(self):
        """Test getting humidity from sensor."""
        humidity = self.client.get_humidity("sensor.humidity")
        
        self.assertIsInstance(humidity, float)
        self.assertEqual(humidity, 65.0)
    
    def test_get_camera_stream(self):
        """Test getting camera stream URL."""
        stream = self.client.get_camera_stream("camera.front_door")
        
        self.assertEqual(stream["entity_id"], "camera.front_door")
        self.assertIn("stream_url", stream)
        self.assertTrue(stream["mock"])
    
    def test_call_service(self):
        """Test calling a service."""
        result = self.client.call_service(
            "light",
            "turn_on",
            {"entity_id": "light.bedroom", "brightness": 150}
        )
        
        self.assertIsInstance(result, list)
        self.assertEqual(result[0]["entity_id"], "light.bedroom")
        self.assertEqual(result[0]["attributes"]["brightness"], 150)
    
    def test_multiple_entities_turn_on(self):
        """Test turning on multiple entities."""
        result = self.client.call_service(
            "light",
            "turn_on",
            {"entity_id": ["light.living_room", "light.bedroom"]}
        )
        
        self.assertEqual(len(result), 2)
        for entity in result:
            self.assertEqual(entity["state"], "on")


class TestHomeAssistantClientWithEnv(unittest.TestCase):
    """Test Home Assistant client with environment variables."""
    
    def test_env_url_token(self):
        """Test that client reads URL and token from environment."""
        # Save current env
        old_url = os.environ.get("HOME_ASSISTANT_URL")
        old_token = os.environ.get("HOME_ASSISTANT_TOKEN")
        
        try:
            os.environ["HOME_ASSISTANT_URL"] = "http://test.local:8123"
            os.environ["HOME_ASSISTANT_TOKEN"] = "test_token"
            
            client = HomeAssistantClient()
            
            self.assertEqual(client.url, "http://test.local:8123")
            self.assertEqual(client.token, "test_token")
            self.assertFalse(client._mock)
            
        finally:
            # Restore env
            if old_url:
                os.environ["HOME_ASSISTANT_URL"] = old_url
            else:
                os.environ.pop("HOME_ASSISTANT_URL", None)
            
            if old_token:
                os.environ["HOME_ASSISTANT_TOKEN"] = old_token
            else:
                os.environ.pop("HOME_ASSISTANT_TOKEN", None)


class TestHomeAssistantErrors(unittest.TestCase):
    """Test error handling."""
    
    def setUp(self):
        """Set up test client."""
        self.client = HomeAssistantClient()
    
    def test_entity_not_found_error(self):
        """Test EntityNotFoundError is raised for unknown entity."""
        with self.assertRaises(EntityNotFoundError):
            self.client.get_state("unknown.entity")
    
    def test_error_inheritance(self):
        """Test that custom errors inherit from HomeAssistantError."""
        self.assertTrue(issubclass(AuthenticationError, HomeAssistantError))
        self.assertTrue(issubclass(EntityNotFoundError, HomeAssistantError))


if __name__ == "__main__":
    unittest.main()
