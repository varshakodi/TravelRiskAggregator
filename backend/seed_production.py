from database import engine, SessionLocal
from models import Base, Airport, FlightEdge, DangerZone

def seed_production_network():
    print("[Database] Purging old toy data...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # 1. GLOBAL HUBS WITH DIVERSE RISKS
    print("[Database] Injecting Global Aviation Hubs...")
    airports = [
        Airport(name="Dubai Intl", iata_code="DXB", location="SRID=4326;POINT(55.3644 25.2532)", risk_level="Medium", risk_description="Elevated military airspace traffic.", severity_index=3.0),
        Airport(name="Mumbai Chhatrapati", iata_code="BOM", location="SRID=4326;POINT(72.8697 19.0974)", risk_level="High", risk_description="Severe monsoon cell approaching.", severity_index=7.0),
        Airport(name="Bengaluru Kempegowda", iata_code="BLR", location="SRID=4326;POINT(77.7066 13.1986)", risk_level="Low", risk_description="Clear operations.", severity_index=1.0),
        Airport(name="London Heathrow", iata_code="LHR", location="SRID=4326;POINT(-0.4543 51.4700)", risk_level="Medium", risk_description="Staffing strikes causing delays.", severity_index=2.5),
        Airport(name="Singapore Changi", iata_code="SIN", location="SRID=4326;POINT(103.9915 1.3644)", risk_level="Low", risk_description="Optimal conditions.", severity_index=1.0),
        Airport(name="Tokyo Narita", iata_code="NRT", location="SRID=4326;POINT(140.3929 35.7720)", risk_level="High", risk_description="Typhoon warning in effect.", severity_index=8.0),
        Airport(name="Hong Kong Intl", iata_code="HKG", location="SRID=4326;POINT(113.9145 22.3080)", risk_level="Medium", risk_description="High crosswinds.", severity_index=4.0),
        Airport(name="New York JFK", iata_code="JFK", location="SRID=4326;POINT(-73.7781 40.6413)", risk_level="Low", risk_description="Standard operations.", severity_index=1.0),
        Airport(name="Frankfurt", iata_code="FRA", location="SRID=4326;POINT(8.5622 50.0379)", risk_level="Low", risk_description="Standard operations.", severity_index=1.0),
        Airport(name="Sydney Kingsford", iata_code="SYD", location="SRID=4326;POINT(151.1772 -33.9399)", risk_level="Low", risk_description="Clear operations.", severity_index=1.0),
    ]
    db.add_all(airports)
    db.commit()

    # 2. MASSIVE SPATIAL THREAT ZONES
    print("[Database] Injecting Severe Weather & Conflict Zones...")
    zones = [
        # Middle East Conflict Box
        DangerZone(source_event="Geopolitical Intelligence", description="Active military airspace. Total airspace closure.", risk_level=10, boundary="SRID=4326;POLYGON((50.0 20.0, 60.0 20.0, 60.0 30.0, 50.0 30.0, 50.0 20.0))"),
        # Bay of Bengal Cyclone (Weather)
        DangerZone(source_event="Aviation Weather Center", description="Category 4 Tropical Cyclone. Severe turbulence FL300-FL400.", risk_level=8, boundary="SRID=4326;POLYGON((85.0 10.0, 95.0 10.0, 95.0 20.0, 85.0 20.0, 85.0 10.0))"),
        # East Asia Typhoon (Weather)
        DangerZone(source_event="NOAA Satellite Feed", description="Typhoon approaching Japanese coast. Zero visibility.", risk_level=9, boundary="SRID=4326;POLYGON((135.0 30.0, 145.0 30.0, 145.0 40.0, 135.0 40.0, 135.0 30.0))")
    ]
    db.add_all(zones)
    db.commit()

    # 3. INTERLOCKING GLOBAL FLIGHT PATHS
    print("[Database] Routing global network edges...")
    edges = [
        # Asian / Middle East Corridors
        FlightEdge(source_iata="DXB", dest_iata="BOM", base_distance_km=1920.0, route_risk_modifier=6.0), # Hits conflict zone
        FlightEdge(source_iata="DXB", dest_iata="BLR", base_distance_km=2700.0, route_risk_modifier=0.0), # Safe detour
        FlightEdge(source_iata="BOM", dest_iata="SIN", base_distance_km=3900.0, route_risk_modifier=7.0), # Hits Cyclone
        FlightEdge(source_iata="BLR", dest_iata="SIN", base_distance_km=3200.0, route_risk_modifier=0.0), # Safe detour
        FlightEdge(source_iata="SIN", dest_iata="HKG", base_distance_km=2580.0, route_risk_modifier=0.0),
        FlightEdge(source_iata="HKG", dest_iata="NRT", base_distance_km=2880.0, route_risk_modifier=8.0), # Hits Typhoon
        
        # Euro / Atlantic Corridors
        FlightEdge(source_iata="DXB", dest_iata="FRA", base_distance_km=4850.0, route_risk_modifier=0.0),
        FlightEdge(source_iata="FRA", dest_iata="LHR", base_distance_km=650.0, route_risk_modifier=0.0),
        FlightEdge(source_iata="LHR", dest_iata="JFK", base_distance_km=5570.0, route_risk_modifier=0.0),
        FlightEdge(source_iata="SIN", dest_iata="SYD", base_distance_km=6300.0, route_risk_modifier=0.0),
    ]
    db.add_all(edges)
    db.commit()
    db.close()
    print("✅ Enterprise database loaded successfully.")

if __name__ == "__main__":
    seed_production_network()