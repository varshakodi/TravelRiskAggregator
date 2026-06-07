from database import engine, SessionLocal
from models import Base, Airport, FlightEdge

def seed_global_network():
    print("[Graph] Purging local database network...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    print("[Graph] Injecting global hub nodes...")
    
    airports = [
        Airport(name="Dubai International", iata_code="DXB", location="SRID=4326;POINT(55.3644 25.2532)", risk_level="Medium", risk_description="Regional airspace monitoring active.", severity_index=2.0),
        Airport(name="Kempegowda International", iata_code="BLR", location="SRID=4326;POINT(77.7066 13.1986)", risk_level="Low", risk_description="Normal operations.", severity_index=1.0),
        Airport(name="Chhatrapati Shivaji Maharaj", iata_code="BOM", location="SRID=4326;POINT(72.8697 19.0974)", risk_level="Low", risk_description="Normal operations.", severity_index=1.0),
        Airport(name="London Heathrow", iata_code="LHR", location="SRID=4326;POINT(-0.4543 51.4700)", risk_level="Low", risk_description="Normal operations.", severity_index=1.0),
        Airport(name="Singapore Changi", iata_code="SIN", location="SRID=4326;POINT(103.9915 1.3644)", risk_level="Low", risk_description="Normal operations.", severity_index=1.0),
        Airport(name="John F. Kennedy International", iata_code="JFK", location="SRID=4326;POINT(-73.7781 40.6413)", risk_level="Low", risk_description="Heavy domestic traffic delays.", severity_index=1.1),
        Airport(name="Paris Charles de Gaulle", iata_code="CDG", location="SRID=4326;POINT(2.5479 49.0097)", risk_level="Low", risk_description="Normal operations.", severity_index=1.0),
        Airport(name="Frankfurt Airport", iata_code="FRA", location="SRID=4326;POINT(8.5622 50.0379)", risk_level="Low", risk_description="Normal operations.", severity_index=1.0)
    ]
    db.add_all(airports)
    db.commit()

    print("[Graph] Building interlocking flight edges...")
    edges = [
        # Middle East & India
        FlightEdge(source_iata="DXB", dest_iata="BLR", base_distance_km=2700.0, route_risk_modifier=8.0), # High risk leg
        FlightEdge(source_iata="DXB", dest_iata="BOM", base_distance_km=1920.0, route_risk_modifier=0.0),
        FlightEdge(source_iata="BOM", dest_iata="BLR", base_distance_km=840.0, route_risk_modifier=0.0),
        
        # Europe Connections
        FlightEdge(source_iata="DXB", dest_iata="LHR", base_distance_km=5470.0, route_risk_modifier=1.5),
        FlightEdge(source_iata="DXB", dest_iata="CDG", base_distance_km=5240.0, route_risk_modifier=1.2),
        FlightEdge(source_iata="LHR", dest_iata="CDG", base_distance_km=340.0, route_risk_modifier=0.0),
        FlightEdge(source_iata="CDG", dest_iata="FRA", base_distance_km=450.0, route_risk_modifier=0.0),
        
        # Transatlantic & Trans-Asian Transits
        FlightEdge(source_iata="LHR", dest_iata="JFK", base_distance_km=5570.0, route_risk_modifier=0.0),
        FlightEdge(source_iata="FRA", dest_iata="DXB", base_distance_km=4850.0, route_risk_modifier=1.0),
        FlightEdge(source_iata="BLR", dest_iata="SIN", base_distance_km=3200.0, route_risk_modifier=0.0),
        FlightEdge(source_iata="BOM", dest_iata="SIN", base_distance_km=3900.0, route_risk_modifier=0.0)
    ]
    db.add_all(edges)
    db.commit()
    db.close()
    print("✅ Global aviation graph seeded successfully.")

if __name__ == "__main__":
    seed_global_network()