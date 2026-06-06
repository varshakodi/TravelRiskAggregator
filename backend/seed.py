from sqlalchemy.orm import Session
from sqlalchemy import text
from database import engine, SessionLocal
from models import Base, Airport

def seed_data():
    print("Dropping old tables...")
    Base.metadata.drop_all(bind=engine)
    
    print("Creating upgraded tables with risk columns...")
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    
    # Create DXB (with a High risk alert)
    dxb = Airport(
        name="Dubai International Airport",
        iata_code="DXB",
        location="SRID=4326;POINT(55.3644 25.2532)",
        risk_level="High",
        risk_description="Airspace congestion and regional delays."
    )
    
    # Create BLR (with a Low risk alert)
    blr = Airport(
        name="Kempegowda International Airport",
        iata_code="BLR",
        location="SRID=4326;POINT(77.7066 13.1986)",
        risk_level="Low",
        risk_description="Clear weather. Normal operations."
    )
    
    db.add(dxb)
    db.add(blr)
    db.commit()
    
    print("✅ Upgraded airports seeded successfully!")
    db.close()

if __name__ == "__main__":
    seed_data()