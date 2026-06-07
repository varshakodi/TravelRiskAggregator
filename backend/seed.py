from database import engine, SessionLocal
from models import Base, Airport, FlightEdge, DangerZone

def seed_data():
    print("Dropping old tables...")
    Base.metadata.drop_all(bind=engine)
    
    print("Creating upgraded tables with Network Graph...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # 1. CREATE NODES (Airports with custom severity levels)
    print("Seeding airports...")
    dxb = Airport(name="Dubai International", iata_code="DXB", location="SRID=4326;POINT(55.3644 25.2532)", risk_level="Medium", risk_description="Elevated regional tensions.", severity_index=2.0)
    blr = Airport(name="Kempegowda International", iata_code="BLR", location="SRID=4326;POINT(77.7066 13.1986)", risk_level="Low", risk_description="Clear weather.", severity_index=1.0)
    bom = Airport(name="Chhatrapati Shivaji Maharaj", iata_code="BOM", location="SRID=4326;POINT(72.8697 19.0974)", risk_level="Low", risk_description="Normal operations.", severity_index=1.0)
    
    db.add_all([dxb, blr, bom])
    db.commit()

    # 2. CREATE EDGES (Flight paths with risk penalties)
    print("Seeding flight network edges...")
    edges = [
        # Direct path gets assigned a severe risk modifier
        FlightEdge(source_iata="DXB", dest_iata="BLR", base_distance_km=2700.0, route_risk_modifier=8.0), 
        # Safe detour path legs
        FlightEdge(source_iata="DXB", dest_iata="BOM", base_distance_km=1920.0, route_risk_modifier=0.0), 
        FlightEdge(source_iata="BOM", dest_iata="BLR", base_distance_km=840.0, route_risk_modifier=0.0),  
    ]
    
    db.add_all(edges)
    db.commit()

    # 3. CREATE SPATIAL DANGER ZONES (Simulates autonomous conflict tracking)
    print("Seeding automated crisis polygons...")
    conflict_zone = DangerZone(
        source_event="Automated News Ingestion",
        description="Airspace closed due to escalating regional conflict over international waters.",
        risk_level=8,
        boundary="SRID=4326;POLYGON((62.0 22.0, 70.0 22.0, 70.0 15.0, 62.0 15.0, 62.0 22.0))"
    )
    db.add(conflict_zone)
    db.commit()
    
    print("✅ Risk-Aware Network Graph seeded successfully!")
    db.close()

if __name__ == "__main__":
    seed_data()