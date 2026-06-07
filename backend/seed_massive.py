import itertools
from database import engine, SessionLocal
from models import Base, Airport, FlightEdge, DangerZone

def seed_massive_network():
    print("[Database] Purging old network...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # 1. 35 GLOBAL HUBS
    print("[Database] Injecting Global Aviation Matrix...")
    airport_data = [
        # North America
        ("JFK", "New York JFK", -73.7781, 40.6413), ("LAX", "Los Angeles Intl", -118.4085, 33.9416),
        ("ORD", "Chicago O'Hare", -87.9073, 41.9742), ("YYZ", "Toronto Pearson", -79.6248, 43.6777),
        ("MEX", "Mexico City Intl", -99.0721, 19.4361), ("MIA", "Miami Intl", -80.2870, 25.7959),
        # South America
        ("GRU", "São Paulo Guarulhos", -46.4731, -23.4356), ("BOG", "Bogotá El Dorado", -74.1469, 4.7016),
        ("SCL", "Santiago Arturo Merino", -70.7858, -33.3930), ("EZE", "Buenos Aires Ezeiza", -58.5348, -34.8222),
        # Europe
        ("LHR", "London Heathrow", -0.4543, 51.4700), ("CDG", "Paris Charles de Gaulle", 2.5479, 49.0097),
        ("FRA", "Frankfurt", 8.5622, 50.0379), ("AMS", "Amsterdam Schiphol", 4.7639, 52.3086),
        ("MAD", "Madrid Barajas", -3.5673, 40.4983), ("FCO", "Rome Fiumicino", 12.2389, 41.7999),
        ("IST", "Istanbul Intl", 28.8146, 41.2609),
        # Africa
        ("JNB", "Johannesburg OR Tambo", 28.2460, -26.1392), ("CAI", "Cairo Intl", 31.4056, 30.1219),
        ("ADD", "Addis Ababa Bole", 38.7993, 8.9779), ("LOS", "Lagos Murtala Muhammed", 3.3215, 6.5774),
        # Middle East
        ("DXB", "Dubai Intl", 55.3644, 25.2532), ("DOH", "Doha Hamad", 51.6080, 25.2730),
        ("RUH", "Riyadh King Khalid", 46.6988, 24.9576), ("TLV", "Tel Aviv Ben Gurion", 34.8856, 32.0114),
        # Asia
        ("PEK", "Beijing Capital", 116.5845, 40.0801), ("HND", "Tokyo Haneda", 139.7798, 35.5494),
        ("SIN", "Singapore Changi", 103.9915, 1.3644), ("HKG", "Hong Kong Intl", 113.9145, 22.3080),
        ("DEL", "Delhi Indira Gandhi", 77.1025, 28.5562), ("BOM", "Mumbai Chhatrapati", 72.8697, 19.0974),
        ("BLR", "Bengaluru Kempegowda", 77.7066, 13.1986), ("BKK", "Bangkok Suvarnabhumi", 100.7501, 13.6811),
        # Oceania
        ("SYD", "Sydney Kingsford", 151.1772, -33.9399), ("MEL", "Melbourne Tullamarine", 144.8433, -37.6690),
        ("AKL", "Auckland", 174.7986, -37.0082)
    ]

    airports = []
    for code, name, lon, lat in airport_data:
        # Assign random light risk to make the map look active
        risk_lvl = "Low"
        idx = 1.0
        if code in ["BOM", "HND", "MIA"]: 
            risk_lvl = "High"
            idx = 8.0
        elif code in ["DXB", "LHR", "JNB", "MEX"]:
            risk_lvl = "Medium"
            idx = 4.0
            
        airports.append(Airport(
            name=name, iata_code=code, 
            location=f"SRID=4326;POINT({lon} {lat})", 
            risk_level=risk_lvl, severity_index=idx
        ))
    db.add_all(airports)
    db.commit()

    # 2. DANGER ZONES
    print("[Database] Mapping Threat Zones...")
    zones = [
        DangerZone(source_event="Geopolitical Intelligence", description="Active military airspace.", risk_level=10, boundary="SRID=4326;POLYGON((50.0 20.0, 60.0 20.0, 60.0 30.0, 50.0 30.0, 50.0 20.0))"),
        DangerZone(source_event="Aviation Weather Center", description="Category 4 Cyclone.", risk_level=8, boundary="SRID=4326;POLYGON((85.0 10.0, 95.0 10.0, 95.0 20.0, 85.0 20.0, 85.0 10.0))"),
        DangerZone(source_event="NOAA Satellite", description="Typhoon warning.", risk_level=9, boundary="SRID=4326;POLYGON((135.0 30.0, 145.0 30.0, 145.0 40.0, 135.0 40.0, 135.0 30.0))")
    ]
    db.add_all(zones)
    db.commit()

    # 3. GENERATING THE GLOBAL WEB (Connected Hubs)
    print("[Database] Routing global network edges...")
    edges = []
    
    # Define major trunk lines to ensure the graph is fully connected
    hubs = ["JFK", "LHR", "DXB", "SIN", "SYD"]
    
    # Connect all major hubs to each other (The Backbone)
    for pair in itertools.combinations(hubs, 2):
        edges.append(FlightEdge(source_iata=pair[0], dest_iata=pair[1], base_distance_km=5000.0, route_risk_modifier=0.0))

    # Connect regional nodes to their nearest hub
    hub_map = {
        "JFK": ["LAX", "ORD", "YYZ", "MEX", "MIA", "BOG", "GRU"],
        "LHR": ["CDG", "FRA", "AMS", "MAD", "FCO", "IST", "CAI", "LOS"],
        "DXB": ["ADD", "JNB", "DOH", "RUH", "TLV", "DEL", "BOM", "BLR"],
        "SIN": ["PEK", "HND", "HKG", "BKK", "MEL"],
        "SYD": ["MEL", "AKL", "SIN", "LAX", "SCL"]
    }

    for hub, regionals in hub_map.items():
        for reg in regionals:
            edges.append(FlightEdge(source_iata=hub, dest_iata=reg, base_distance_km=1500.0, route_risk_modifier=0.0))

    # Add the dangerous routes to force Dijkstra to recalculate
    edges.append(FlightEdge(source_iata="DXB", dest_iata="BOM", base_distance_km=1920.0, route_risk_modifier=8.0)) # War Zone
    edges.append(FlightEdge(source_iata="BOM", dest_iata="SIN", base_distance_km=3900.0, route_risk_modifier=7.0)) # Cyclone
    edges.append(FlightEdge(source_iata="HKG", dest_iata="HND", base_distance_km=2880.0, route_risk_modifier=8.0)) # Typhoon

    db.add_all(edges)
    db.commit()
    db.close()
    print("✅ Global Aviation Graph (35 Nodes) seeded successfully.")

if __name__ == "__main__":
    seed_massive_network()