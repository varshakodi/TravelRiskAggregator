import itertools
import requests
from database import engine, SessionLocal
from models import Base, Airport, FlightEdge, DangerZone

def fetch_airports():
    # Public JSON file with global airports
    url = "https://raw.githubusercontent.com/jbrooksuk/JSON-Airports/master/airports.json"
    print(f"[API] Fetching airports from {url} ...")
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def seed_dynamic_network():
    print("[Database] Purging old network...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # The subset of IATA codes we actually want to load to avoid exploding the graph size.
    # We ensure HND, BLR, BOM, DXB, SIN, etc. are included to match the demo scenario.
    target_iatas = {
        "JFK", "LAX", "ORD", "YYZ", "MEX", "MIA", "GRU", "BOG", "SCL", "EZE",
        "LHR", "CDG", "FRA", "AMS", "MAD", "FCO", "IST", "JNB", "CAI", "ADD",
        "LOS", "DXB", "DOH", "RUH", "TLV", "PEK", "HND", "SIN", "HKG", "DEL",
        "BOM", "BLR", "BKK", "SYD", "MEL", "AKL"
    }

    print("[Database] Processing API data and Injecting Aviation Matrix...")
    raw_airports = fetch_airports()
    
    airports = []
    fetched_codes = set()
    coord_map = {}   # iata -> (lon, lat) for haversine distance calc later
    
    for a in raw_airports:
        code = a.get("iata")
        if code in target_iatas and code not in fetched_codes:
            fetched_codes.add(code)
            name = a.get("name") or f"Airport {code}"
            try:
                lon = float(a.get("lon"))
                lat = float(a.get("lat"))
            except (TypeError, ValueError):
                continue

            coord_map[code] = (lon, lat)  # store for distance calc
                
            risk_lvl = "Low"
            idx = 1.0
            if code in ["BOM", "HND", "MIA"]: 
                risk_lvl = "High"
                idx = 8.0
            elif code in ["DXB", "LHR", "JNB", "MEX"]:
                risk_lvl = "Medium"
                idx = 4.0
                
            airports.append(Airport(
                name=name, 
                iata_code=code, 
                location=f"SRID=4326;POINT({lon} {lat})", 
                risk_level=risk_lvl, 
                severity_index=idx
            ))
            
    db.add_all(airports)
    db.commit()

    print(f"[Database] Loaded {len(airports)} targeted airports from external API.")


    # 2. DANGER ZONES — geographically accurate, verified not to overlap hub airports
    print("[Database] Mapping Threat Zones...")
    zones = [
        # Iran/Iraq restricted airspace — above the Gulf coast (lat > 30), DXB is at lat 25 so safe
        DangerZone(
            source_event="Geopolitical Intelligence",
            description="Iran & Iraq restricted airspace. ICAO NOTAMs active.",
            risk_level=10,
            boundary="SRID=4326;POLYGON((44 30, 63 30, 63 38, 44 38, 44 30))"
        ),
        # Ukraine/Belarus airspace closure — European conflict zone
        DangerZone(
            source_event="EUROCONTROL NOTAM",
            description="Ukraine & Belarus airspace closed to civil aviation.",
            risk_level=9,
            boundary="SRID=4326;POLYGON((22 46, 40 46, 40 54, 22 54, 22 46))"
        ),
        # Philippine Sea typhoon corridor — east of Taiwan, well away from HND(139.8,35.5)
        DangerZone(
            source_event="NOAA Typhoon Warning",
            description="Active typhoon corridor. Category 4 system tracked.",
            risk_level=8,
            boundary="SRID=4326;POLYGON((125 18, 138 18, 138 30, 125 30, 125 18))"
        ),
    ]
    db.add_all(zones)
    db.commit()

    # 3. GENERATING THE GLOBAL WEB — edges use real geodesic distances
    import math
    print("[Database] Routing global network edges with real distances...")

    def haversine(iata1, iata2):
        """Return great-circle distance in km between two IATA airports."""
        lon1, lat1 = coord_map[iata1]
        lon2, lat2 = coord_map[iata2]
        R = 6371.0
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
        return round(R * 2 * math.asin(math.sqrt(a)), 1)

    edges = []
    hubs = ["JFK", "LHR", "DXB", "SIN", "SYD"]
    available_hubs = [h for h in hubs if h in fetched_codes and h in coord_map]

    # Backbone: connect all major hubs to each other with real distances
    for pair in itertools.combinations(available_hubs, 2):
        dist = haversine(pair[0], pair[1])
        edges.append(FlightEdge(source_iata=pair[0], dest_iata=pair[1], base_distance_km=dist, route_risk_modifier=0.0))

    # Regional: connect each regional airport to its nearest hub with real distance
    hub_map = {
        "JFK": ["LAX", "ORD", "YYZ", "MEX", "MIA", "BOG", "GRU"],
        "LHR": ["CDG", "FRA", "AMS", "MAD", "FCO", "IST", "CAI", "LOS"],
        "DXB": ["ADD", "JNB", "DOH", "RUH", "TLV", "DEL", "BOM", "BLR"],
        "SIN": ["PEK", "HND", "HKG", "BKK", "MEL"],
        "SYD": ["MEL", "AKL", "SIN", "LAX", "SCL"]
    }
    for hub, regionals in hub_map.items():
        if hub not in fetched_codes or hub not in coord_map:
            continue
        for reg in regionals:
            if reg in fetched_codes and reg in coord_map:
                dist = haversine(hub, reg)
                edges.append(FlightEdge(source_iata=hub, dest_iata=reg, base_distance_km=dist, route_risk_modifier=0.0))

    # Extra direct connections for common routes
    extra_pairs = [
        ("DXB", "BOM"), ("BOM", "SIN"), ("HKG", "HND"),
        ("DEL", "BLR"), ("DEL", "BOM"), ("BLR", "SIN"),
        ("IST", "DXB"), ("CAI", "DXB"), ("LHR", "DXB"),
        ("CDG", "DXB"), ("FRA", "DXB"), ("HND", "HKG"),
        ("SIN", "HND"), ("PEK", "HND"),
    ]
    for a1, a2 in extra_pairs:
        if a1 in fetched_codes and a2 in fetched_codes and a1 in coord_map and a2 in coord_map:
            dist = haversine(a1, a2)
            edges.append(FlightEdge(source_iata=a1, dest_iata=a2, base_distance_km=dist, route_risk_modifier=0.0))

    db.add_all(edges)
    db.commit()
    db.close()
    print(f"✅ Dynamic Global Aviation Graph seeded with {len(edges)} edges and real distances.")

if __name__ == "__main__":
    seed_dynamic_network()
