from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text, func

from database import engine, SessionLocal
from models import Base, Airport

# 1. Setup Database Extension on Startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    with engine.connect() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        connection.commit()
    Base.metadata.create_all(bind=engine)
    yield

# 2. Initialize FastAPI App 
app = FastAPI(lifespan=lifespan)

# 3. Add Security/CORS Middleware so React can connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Database Connection Helper
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- API ENDPOINTS ---

@app.get("/")
def read_root():
    return {"message": "API is running!"}

@app.get("/api/airports")
def get_all_airports(db: Session = Depends(get_db)):
    # Fetch airports AND the new risk columns from the database
    airports_data = db.query(
        Airport.id, 
        Airport.name, 
        Airport.iata_code,
        Airport.risk_level,         # <-- NEW
        Airport.risk_description,   # <-- NEW
        func.ST_X(Airport.location).label('lon'),
        func.ST_Y(Airport.location).label('lat')
    ).all()
    
    results = []
    for a in airports_data:
        results.append({
            "id": a.id,
            "name": a.name,
            "iata_code": a.iata_code,
            "risk_level": a.risk_level,             # <-- NEW
            "risk_description": a.risk_description, # <-- NEW
            "lon": a.lon,
            "lat": a.lat
        })
        
    return {"airports": results}

@app.get("/api/distance")
def calculate_flight_distance(origin: str, destination: str, db: Session = Depends(get_db)):
    """
    Calculates the great-circle distance between two airports using PostGIS.
    """
    orig_airport = db.query(Airport).filter(Airport.iata_code == origin.upper()).first()
    dest_airport = db.query(Airport).filter(Airport.iata_code == destination.upper()).first()
    
    if not orig_airport or not dest_airport:
        raise HTTPException(status_code=404, detail="One or both airports not found")
        
    # Ask the database directly using raw SQL to handle the spatial math
    query = text(f"""
        SELECT ST_Distance(
            (SELECT location FROM {Airport.__tablename__} WHERE iata_code = :origin)::geography,
            (SELECT location FROM {Airport.__tablename__} WHERE iata_code = :dest)::geography
        )
    """)
    
    distance_meters = db.execute(query, {"origin": origin.upper(), "dest": destination.upper()}).scalar()
    
    distance_km = distance_meters / 1000.0
    distance_miles = distance_km * 0.621371
    
    return {
        "origin": {"name": orig_airport.name, "iata": orig_airport.iata_code},
        "destination": {"name": dest_airport.name, "iata": dest_airport.iata_code},
        "distance_km": round(distance_km, 2),
        "distance_miles": round(distance_miles, 2)
    }