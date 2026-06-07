import json
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Base, Airport, FlightEdge, DangerZone
from services.pathfinder import calculate_optimal_route

# Make sure all tables exist
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Allow your React frontend to connect without getting blocked by CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get database access per request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class RouteRequest(BaseModel):
    origin: str
    destination: str

@app.get("/api/airports")
def get_airports(db: Session = Depends(get_db)):
    # Pulls airports and converts PostGIS POINT geometry into lat/lon coordinates
    query = text("""
        SELECT id, name, iata_code, risk_level, risk_description, 
               ST_X(location::geometry) as lon, ST_Y(location::geometry) as lat 
        FROM airports
    """)
    result = db.execute(query).fetchall()
    
    airports = []
    for row in result:
        airports.append({
            "id": row.id,
            "name": row.name,
            "iata_code": row.iata_code,
            "risk_level": row.risk_level,
            "risk_description": row.risk_description,
            "lon": row.lon,
            "lat": row.lat
        })
    return {"airports": airports}

@app.get("/api/danger-zones")
def get_danger_zones(db: Session = Depends(get_db)):
    # Pulls automated risk zones and converts PostGIS POLYGON into GeoJSON
    query = text("""
        SELECT id, source_event, description, risk_level, ST_AsGeoJSON(boundary) as geojson 
        FROM danger_zones
    """)
    result = db.execute(query).fetchall()
    
    zones = []
    for row in result:
        zones.append({
            "id": row.id,
            "source": row.source_event,
            "description": row.description,
            "severity": row.risk_level,
            "boundary": json.loads(row.geojson)
        })
    return {"zones": zones}

@app.post("/api/route/calculate")
def calculate_route(req: RouteRequest, db: Session = Depends(get_db)):
    route = calculate_optimal_route(db, req.origin, req.destination)
    if not route:
        raise HTTPException(status_code=404, detail="No optimal route could be computed.")
    return route