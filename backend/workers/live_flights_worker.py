"""
Live flight data integration:
- AviationStack API: Real scheduled/active flight data (airline, status, delays) per route
- OpenSky Network: Real-time aircraft positions for the global map overlay (free, no auth)
"""
import os
import requests
from typing import Optional

AVIATIONSTACK_KEY = os.getenv("AVIATIONSTACK_KEY", "")
AVIATIONSTACK_BASE = "http://api.aviationstack.com/v1"
OPENSKY_BASE = "https://opensky-network.org/api"

# Major hub pairs to query for live AviationStack route intelligence
HUB_PAIRS = [
    ("HND", "SIN"), ("SIN", "DXB"), ("DXB", "LHR"), ("LHR", "JFK"),
    ("JFK", "LAX"), ("SIN", "BLR"), ("DXB", "BLR"), ("HND", "BKK"),
    ("BKK", "DXB"), ("SIN", "SYD"), ("LHR", "CDG"), ("CDG", "DXB"),
    ("DXB", "DEL"), ("DEL", "BOM"), ("BOM", "BLR"), ("HKG", "SIN"),
]

# Bounding box covering the key flight corridors
OPENSKY_BOUNDS = {
    "lamin": -40.0,  # Southern Australia
    "lamax": 60.0,   # Northern Europe/Russia
    "lomin": -10.0,  # Western Europe
    "lomax": 145.0,  # Eastern Australia
}

# OpenSky state vector field indices
OPENSKY_FIELDS = [
    "icao24", "callsign", "origin_country", "time_position",
    "last_contact", "longitude", "latitude", "baro_altitude",
    "on_ground", "velocity", "true_track", "vertical_rate",
    "sensors", "geo_altitude", "squawk", "spi", "position_source"
]


def fetch_opensky_positions() -> list:
    """
    Fetches real-time aircraft positions from OpenSky Network (free, no auth).
    Returns aircraft currently airborne over major flight corridors.
    """
    try:
        resp = requests.get(
            f"{OPENSKY_BASE}/states/all",
            params=OPENSKY_BOUNDS,
            timeout=12,
        )
        resp.raise_for_status()
        data = resp.json()
        states = data.get("states", []) or []

        aircraft = []
        for state in states:
            if len(state) < 17:
                continue
            icao24, callsign, country = state[0], state[1], state[2]
            lon, lat = state[5], state[6]
            altitude = state[7]       # barometric altitude in meters
            on_ground = state[8]
            velocity = state[9]       # m/s
            heading = state[10]
            callsign = (callsign or "").strip()

            # Filter out ground traffic and aircraft without position
            if on_ground or not lat or not lon or not callsign:
                continue

            # Convert m/s to knots, meters to feet
            speed_kts = round(velocity * 1.94384) if velocity else None
            alt_ft = round(altitude * 3.28084) if altitude else None

            aircraft.append({
                "icao24": icao24,
                "callsign": callsign,
                "country": country,
                "lat": lat,
                "lon": lon,
                "altitude_ft": alt_ft,
                "speed_kts": speed_kts,
                "heading": heading or 0,
                "on_ground": on_ground,
            })

        print(f"[OpenSky] Fetched {len(aircraft)} airborne aircraft.")
        return aircraft

    except Exception as e:
        print(f"[OpenSky] Error fetching aircraft positions: {e}")
        return []


def fetch_route_flights(dep_iata: str, arr_iata: str, limit: int = 10) -> list:
    """
    Fetches real flight schedule/status data for a specific route from AviationStack.
    Returns actual airline names, flight numbers, schedules and delays.
    """
    if not AVIATIONSTACK_KEY:
        return []

    try:
        resp = requests.get(
            f"{AVIATIONSTACK_BASE}/flights",
            params={
                "access_key": AVIATIONSTACK_KEY,
                "dep_iata": dep_iata,
                "arr_iata": arr_iata,
                "limit": limit,
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        raw_flights = data.get("data", []) or []

        results = []
        for f in raw_flights:
            dep = f.get("departure", {})
            arr = f.get("arrival", {})
            airline = f.get("airline", {})
            flight = f.get("flight", {})

            results.append({
                "flight_number": flight.get("iata", ""),
                "airline": airline.get("name", "Unknown"),
                "dep_iata": dep.get("iata", dep_iata),
                "arr_iata": arr.get("iata", arr_iata),
                "dep_airport": dep.get("airport", ""),
                "arr_airport": arr.get("airport", ""),
                "dep_scheduled": dep.get("scheduled", ""),
                "arr_scheduled": arr.get("scheduled", ""),
                "dep_actual": dep.get("actual"),
                "arr_actual": arr.get("actual"),
                "dep_delay": dep.get("delay"),
                "arr_delay": arr.get("delay"),
                "status": f.get("flight_status", "unknown"),
                "terminal": dep.get("terminal"),
                "gate": dep.get("gate"),
            })
        return results

    except Exception as e:
        print(f"[AviationStack] Error fetching {dep_iata}->{arr_iata}: {e}")
        return []


def fetch_all_live_flights() -> list:
    """
    Returns real-time airborne aircraft positions from OpenSky Network.
    This is what gets plotted on the map.
    """
    return fetch_opensky_positions()
