"""
Canonical database seed for local/demo use — DATA ONLY.

Schema is owned by Alembic (run `alembic upgrade head` first); this script
just fills the tables:
  - 36 real-world airport hubs (verified IATA coordinates)
  - Great-circle (haversine) distances for every edge, not flat placeholders
  - 3 danger zones representing plausible scenarios, honestly labeled as
    seed data — NOT live feed output. Live ingestion lives in workers/ and
    is a separate, explicitly-labeled pipeline (see workers/data_ingestion.py).

Re-runnable: clears existing rows (children before parents, so the foreign
keys allow it) and inserts fresh.
"""
import itertools
import math
import sys

from sqlalchemy import inspect

from database import engine, SessionLocal
from models import Airport, FlightEdge, DangerZone

# (iata, name, lon, lat)
AIRPORTS = [
    # North America
    ("JFK", "New York JFK", -73.7781, 40.6413),
    ("LAX", "Los Angeles Intl", -118.4085, 33.9416),
    ("ORD", "Chicago O'Hare", -87.9073, 41.9742),
    ("YYZ", "Toronto Pearson", -79.6248, 43.6777),
    ("MEX", "Mexico City Intl", -99.0721, 19.4361),
    ("MIA", "Miami Intl", -80.2870, 25.7959),
    # South America
    ("GRU", "São Paulo Guarulhos", -46.4731, -23.4356),
    ("BOG", "Bogotá El Dorado", -74.1469, 4.7016),
    ("SCL", "Santiago Arturo Merino", -70.7858, -33.3930),
    ("EZE", "Buenos Aires Ezeiza", -58.5348, -34.8222),
    # Europe
    ("LHR", "London Heathrow", -0.4543, 51.4700),
    ("CDG", "Paris Charles de Gaulle", 2.5479, 49.0097),
    ("FRA", "Frankfurt", 8.5622, 50.0379),
    ("AMS", "Amsterdam Schiphol", 4.7639, 52.3086),
    ("MAD", "Madrid Barajas", -3.5673, 40.4983),
    ("FCO", "Rome Fiumicino", 12.2389, 41.7999),
    ("IST", "Istanbul Intl", 28.8146, 41.2609),
    # Africa
    ("JNB", "Johannesburg OR Tambo", 28.2460, -26.1392),
    ("CAI", "Cairo Intl", 31.4056, 30.1219),
    ("ADD", "Addis Ababa Bole", 38.7993, 8.9779),
    ("LOS", "Lagos Murtala Muhammed", 3.3215, 6.5774),
    # Middle East
    ("DXB", "Dubai Intl", 55.3644, 25.2532),
    ("DOH", "Doha Hamad", 51.6080, 25.2730),
    ("RUH", "Riyadh King Khalid", 46.6988, 24.9576),
    ("TLV", "Tel Aviv Ben Gurion", 34.8856, 32.0114),
    # Asia
    ("PEK", "Beijing Capital", 116.5845, 40.0801),
    ("HND", "Tokyo Haneda", 139.7798, 35.5494),
    ("SIN", "Singapore Changi", 103.9915, 1.3644),
    ("HKG", "Hong Kong Intl", 113.9145, 22.3080),
    ("DEL", "Delhi Indira Gandhi", 77.1025, 28.5562),
    ("BOM", "Mumbai Chhatrapati", 72.8697, 19.0974),
    ("BLR", "Bengaluru Kempegowda", 77.7066, 13.1986),
    ("BKK", "Bangkok Suvarnabhumi", 100.7501, 13.6811),
    # Oceania
    ("SYD", "Sydney Kingsford", 151.1772, -33.9399),
    ("MEL", "Melbourne Tullamarine", 144.8433, -37.6690),
    ("AKL", "Auckland", 174.7986, -37.0082),
]

# Curated flavor text for airports tied to the demo's danger-zone scenarios.
# This is presentation, not a risk model — Phase 1 replaces flat risk_level
# strings with a real weighted score derived from zone proximity/severity.
RISK_OVERRIDES = {
    "DXB": ("Medium", "Elevated regional airspace monitoring.", 3.0),
    "BOM": ("High", "Seasonal monsoon cell activity reported.", 7.0),
    "IST": ("Medium", "Adjacent to active Eastern European NOTAM airspace.", 4.0),
    "HND": ("High", "Typhoon corridor advisory in effect.", 8.0),
    "HKG": ("Medium", "High crosswind advisory.", 4.0),
    "LHR": ("Low", "Standard operations.", 1.5),
}
DEFAULT_RISK = ("Low", "Standard operations.", 1.0)

# Danger zone polygons: geographically placed so they sit over real corridors
# without swallowing hub airports outright. Honestly labeled as seed
# scenarios — compare workers/data_ingestion.py for the live-feed path.
# (external_id, source, description, severity, ring)
# external_id is each zone's stable identity — re-running seed (or a live
# feed re-sending an event) updates the same row instead of creating twins.
DANGER_ZONES = [
    (
        "seed:iran-iraq-airspace",
        "Seed Scenario — Geopolitical",
        "Iran & Iraq restricted airspace. ICAO NOTAMs active.",
        10,
        [(44, 30), (63, 30), (63, 38), (44, 38)],
    ),
    (
        "seed:ukraine-belarus-closure",
        "Seed Scenario — Geopolitical",
        "Ukraine & Belarus airspace closed to civil aviation.",
        9,
        [(22, 46), (40, 46), (40, 54), (22, 54)],
    ),
    (
        "seed:philippine-sea-typhoon",
        "Seed Scenario — Aviation Weather",
        "Active typhoon corridor. Category 4 system tracked.",
        8,
        [(125, 18), (138, 18), (138, 30), (125, 30)],
    ),
]

# Hub backbone + regional spokes. Distances are computed below via haversine,
# not hardcoded, so they stay correct if a coordinate ever changes.
HUBS = ["JFK", "LHR", "DXB", "SIN", "SYD"]
HUB_SPOKES = {
    "JFK": ["LAX", "ORD", "YYZ", "MEX", "MIA", "BOG", "GRU"],
    "LHR": ["CDG", "FRA", "AMS", "MAD", "FCO", "IST", "CAI", "LOS"],
    "DXB": ["ADD", "JNB", "DOH", "RUH", "TLV", "DEL", "BOM", "BLR"],
    "SIN": ["PEK", "HND", "HKG", "BKK", "MEL"],
    "SYD": ["MEL", "AKL", "SIN", "LAX", "SCL"],
}
EXTRA_EDGES = [
    ("DXB", "BOM"), ("BOM", "SIN"), ("HKG", "HND"),
    ("DEL", "BLR"), ("DEL", "BOM"), ("BLR", "SIN"),
    ("IST", "DXB"), ("CAI", "DXB"), ("LHR", "DXB"),
    ("CDG", "DXB"), ("FRA", "DXB"), ("HND", "HKG"),
    ("SIN", "HND"), ("PEK", "HND"),
]


def haversine_km(coord_map, iata1, iata2):
    """Great-circle distance between two airports, in kilometers."""
    lon1, lat1 = coord_map[iata1]
    lon2, lat2 = coord_map[iata2]
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return round(R * 2 * math.asin(math.sqrt(a)), 1)


def seed():
    # Schema is Alembic's job now — fail with a helpful message if it hasn't run.
    if not inspect(engine).has_table("airports"):
        sys.exit("Tables missing. Run `alembic upgrade head` first, then re-run seed.")

    db = SessionLocal()

    # Clear existing rows, children before parents (the foreign keys forbid
    # deleting an airport while edges still reference it).
    print("[Database] Clearing existing rows...")
    db.query(FlightEdge).delete()
    db.query(DangerZone).delete()
    db.query(Airport).delete()
    db.commit()

    print(f"[Database] Inserting {len(AIRPORTS)} airports...")
    coord_map = {code: (lon, lat) for code, _, lon, lat in AIRPORTS}
    airport_rows = []
    for code, name, lon, lat in AIRPORTS:
        risk_level, risk_desc, severity = RISK_OVERRIDES.get(code, DEFAULT_RISK)
        airport_rows.append(Airport(
            name=name,
            iata_code=code,
            location=f"SRID=4326;POINT({lon} {lat})",
            risk_level=risk_level,
            risk_description=risk_desc,
            severity_index=severity,
        ))
    db.add_all(airport_rows)
    db.commit()

    print(f"[Database] Inserting {len(DANGER_ZONES)} danger zones...")
    zone_rows = []
    for external_id, source, description, severity, ring in DANGER_ZONES:
        closed_ring = ring + [ring[0]]
        wkt_points = ", ".join(f"{lon} {lat}" for lon, lat in closed_ring)
        zone_rows.append(DangerZone(
            external_id=external_id,
            source_event=source,
            description=description,
            risk_level=severity,
            boundary=f"SRID=4326;POLYGON(({wkt_points}))",
        ))
    db.add_all(zone_rows)
    db.commit()

    print("[Database] Routing edges with great-circle distances...")
    edge_pairs = set()
    for a, b in itertools.combinations(HUBS, 2):
        edge_pairs.add((a, b))
    for hub, spokes in HUB_SPOKES.items():
        for spoke in spokes:
            edge_pairs.add((hub, spoke))
    for a, b in EXTRA_EDGES:
        edge_pairs.add((a, b))

    edge_rows = []
    for source, dest in sorted(edge_pairs):
        if source not in coord_map or dest not in coord_map:
            continue
        dist = haversine_km(coord_map, source, dest)
        edge_rows.append(FlightEdge(
            source_iata=source,
            dest_iata=dest,
            base_distance_km=dist,
        ))
    db.add_all(edge_rows)
    db.commit()
    db.close()

    print(f"[Database] Seeded {len(airport_rows)} airports, {len(zone_rows)} danger zones, "
          f"{len(edge_rows)} edges.")


if __name__ == "__main__":
    seed()
