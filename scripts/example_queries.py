#!/usr/bin/env python3
"""Example queries for AgendaFlow API."""

import requests
from typing import Dict


def query_api(question: str, **kwargs) -> Dict:
    """Query the AgendaFlow API.

    Args:
        question: Question to ask
        **kwargs: Additional parameters (category, price, etc.)

    Returns:
        API response
    """
    url = "http://localhost:8000/ask"

    payload = {"question": question, **kwargs}

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error querying API: {e}")
        return {}


def print_response(response: Dict):
    """Pretty print API response.

    Args:
        response: API response
    """
    if not response:
        return

    print("\n" + "=" * 60)
    print("ANSWER:")
    print("=" * 60)
    print(response.get("answer", "No answer"))
    print()

    events = response.get("events", [])
    if events:
        print("=" * 60)
        print(f"EVENTS ({len(events)}):")
        print("=" * 60)
        for i, event in enumerate(events, 1):
            print(f"\n{i}. {event.get('title', 'Unknown')}")
            print(f"   📅 {event.get('start_datetime', 'N/A')}")
            print(f"   📍 {event.get('venue_name', 'N/A')}, {event.get('city', 'N/A')}")
            if event.get("arrondissement"):
                print(f"   🏛️  {event.get('arrondissement')}")
            print(f"   💰 {event.get('price', 'N/A')}")
            if event.get("url"):
                print(f"   🔗 {event.get('url')}")
    print()
    print("=" * 60)
    print(f"⏱️  Latency: {response.get('latency_ms', 0)}ms")
    print("=" * 60)
    print()


def main():
    """Run example queries."""
    print("=" * 60)
    print("AgendaFlow API - Example Queries")
    print("=" * 60)
    print()
    print("Make sure the API is running on http://localhost:8000")
    print()

    # Check if API is up
    try:
        health = requests.get("http://localhost:8000/health", timeout=5)
        if health.status_code != 200:
            print("❌ API is not responding properly")
            return
        print("✓ API is healthy")
    except requests.exceptions.RequestException:
        print("❌ Could not connect to API")
        print("Please start the API with: uvicorn api.main:app")
        return

    print()

    # Example 1: Jazz concerts this weekend
    print("\n📝 Example 1: Jazz concerts this weekend")
    response = query_api("Quels concerts de jazz ce week-end ?")
    print_response(response)

    # Example 2: Free events for kids
    print("\n📝 Example 2: Free events for kids")
    response = query_api("Free events for kids today", category="kids", price="free")
    print_response(response)

    # Example 3: Exhibitions in specific arrondissement
    print("\n📝 Example 3: Exhibitions in the 11th arrondissement")
    response = query_api(
        "Expositions dans le 11e arrondissement", category="exhibition", arrondissement=11
    )
    print_response(response)

    # Example 4: Theater next week
    print("\n📝 Example 4: Theater next week")
    response = query_api("What theater performances next week?", category="theater")
    print_response(response)

    # Example 5: General query
    print("\n📝 Example 5: What's happening tonight?")
    response = query_api("What's happening tonight in Paris?")
    print_response(response)

    print("\n✨ Done! Try your own queries at http://localhost:8000/docs")


if __name__ == "__main__":
    main()
