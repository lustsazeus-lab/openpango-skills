#!/usr/bin/env python3
"""
Home Assistant Integration for OpenPango
Provides tools to interact with Home Assistant instances.
"""
import os
import json
import argparse
import urllib.request
import urllib.error
from typing import Optional, Dict, Any


def get_ha_url() -> str:
    """Get Home Assistant URL from environment or config."""
    return os.environ.get("HA_URL", "http://homeassistant.local:8123")


def get_ha_token() -> str:
    """Get Home Assistant access token from environment."""
    token = os.environ.get("HA_TOKEN")
    if not token:
        raise ValueError("HA_TOKEN environment variable not set. Please configure your Home Assistant access token.")
    return token


def make_request(method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
    """Make an authenticated request to Home Assistant API."""
    url = f"{get_ha_url()}/api/{endpoint}"
    headers = {
        "Authorization": f"Bearer {get_ha_token()}",
        "Content-Type": "application/json",
    }
    
    request_data = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=request_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else ""
        raise Exception(f"Home Assistant API error ({e.code}): {error_body}")
    except urllib.error.URLError as e:
        raise Exception(f"Failed to connect to Home Assistant: {e.reason}")


def get_states() -> list:
    """Get all entity states."""
    return make_request("GET", "states")


def get_state(entity_id: str) -> Dict[str, Any]:
    """Get state of a specific entity."""
    return make_request("GET", f"states/{entity_id}")


def call_service(domain: str, service: str, service_data: Optional[Dict] = None) -> Dict[str, Any]:
    """Call a Home Assistant service."""
    if service_data is None:
        service_data = {}
    return make_request("POST", f"services/{domain}/{service}", service_data)


def list_entities(domain: Optional[str] = None) -> list:
    """List all entities, optionally filtered by domain."""
    states = get_states()
    if domain:
        return [s for s in states if s["entity_id"].startswith(f"{domain}.")]
    return states


def get_config() -> Dict[str, Any]:
    """Get Home Assistant configuration."""
    return make_request("GET", "config")


def get_services() -> Dict[str, Any]:
    """Get all available services."""
    return make_request("GET", "services")


def main():
    parser = argparse.ArgumentParser(description="Home Assistant Integration for OpenPango")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # get-state command
    state_parser = subparsers.add_parser("get-state", help="Get entity state")
    state_parser.add_argument("entity_id", help="Entity ID (e.g., light.living_room)")
    
    # call-service command
    service_parser = subparsers.add_parser("call-service", help="Call a service")
    service_parser.add_argument("domain", help="Domain (e.g., light)")
    service_parser.add_argument("service", help="Service (e.g., turn_on)")
    service_parser.add_argument("--data", "-d", help="JSON service data")
    
    # list-entities command
    list_parser = subparsers.add_parser("list-entities", help="List entities")
    list_parser.add_argument("--domain", "-d", help="Filter by domain")
    
    # get-states command
    subparsers.add_parser("get-states", help="Get all states")
    
    # get-services command
    subparsers.add_parser("get-services", help="Get all services")
    
    # get-config command
    subparsers.add_parser("get-config", help="Get HA config")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == "get-state":
            result = get_state(args.entity_id)
            print(json.dumps(result, indent=2))
        
        elif args.command == "call-service":
            data = json.loads(args.data) if args.data else {}
            result = call_service(args.domain, args.service, data)
            print(json.dumps(result, indent=2))
        
        elif args.command == "list-entities":
            result = list_entities(args.domain)
            print(json.dumps(result, indent=2))
        
        elif args.command == "get-states":
            result = get_states()
            print(json.dumps(result, indent=2))
        
        elif args.command == "get-services":
            result = get_services()
            print(json.dumps(result, indent=2))
        
        elif args.command == "get-config":
            result = get_config()
            print(json.dumps(result, indent=2))
    
    except Exception as e:
        print(json.dumps({"error": str(e)}), file=__import__("sys").stderr)
        exit(1)


if __name__ == "__main__":
    main()
