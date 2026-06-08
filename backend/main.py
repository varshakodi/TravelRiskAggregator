import json
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import Base
from services.pathfinder import calculate_route_comparison
from services.ai_service import generate_threat_briefing
from workers.aviation_worker import fetch_aviation_weather_alerts
from workers.live_flights_worker import fetch_all_live_flights, fetch_route_flights

# NEW: Import the background scheduler and our ingestion logic
from apscheduler.schedulers.background import BackgroundScheduler
from workers.data_ingestion import fetch_live_risk_data

# Ensure database architecture is built
Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CRON SCHEDULER LIFECYCLE ---
@app.on_event("startup")
def start_data_pipelines():
    # NOTE: Schedulers disabled to prevent duplicate zone insertion.
    # Re-enable when connected to real ACLED/weather API keys.
    # scheduler = BackgroundScheduler()
    # scheduler.add_job(fetch_live_risk_data, 'interval', seconds=60)
    # scheduler.add_job(fetch_aviation_weather_alerts, 'interval', seconds=60)
    # scheduler.start()
    print("[Engine] Static threat zones active. Live ingestion paused (no API keys configured).")

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
    query = text("""
        SELECT id, name, iata_code, risk_level, risk_description, 
               ST_X(location::geometry) as lon, ST_Y(location::geometry) as lat 
        FROM airports
    """)
    result = db.execute(query).fetchall()
    return {"airports": [{"id": r.id, "name": r.name, "iata_code": r.iata_code, "risk_level": r.risk_level, "risk_description": r.risk_description, "lon": r.lon, "lat": r.lat} for r in result]}

@app.get("/api/danger-zones")
def get_danger_zones(db: Session = Depends(get_db)):
    query = text("""
        SELECT id, source_event, description, risk_level, ST_AsGeoJSON(boundary) as geojson 
        FROM danger_zones
    """)
    result = db.execute(query).fetchall()
    return {"zones": [{"id": r.id, "source": r.source_event, "description": r.description, "severity": r.risk_level, "boundary": json.loads(r.geojson)} for r in result]}

@app.post("/api/route/calculate")
def calculate_route(req: RouteRequest, db: Session = Depends(get_db)):
    result = calculate_route_comparison(db, req.origin, req.destination)
    if not result["standard_route"]:
        raise HTTPException(status_code=404, detail="No optimal route could be computed.")
    return result

class BriefingRequest(BaseModel):
    origin: str
    destination: str
    standard_route: list
    safe_route: list
    is_rerouted: bool

@app.post("/api/route/briefing")
def get_ai_briefing(req: BriefingRequest):
    briefing = generate_threat_briefing(
        req.origin, 
        req.destination, 
        req.standard_route, 
        req.safe_route, 
        req.is_rerouted
    )
    return {"briefing": briefing}


@app.get("/api/live-flights")
def get_live_flights():
    """
    Returns real-time aircraft positions for the global map overlay.
    Fetches live flights across major hub routes from AviationStack.
    """
    flights = fetch_all_live_flights()
    return {"flights": flights, "count": len(flights)}


@app.get("/api/live-flights/{dep_iata}/{arr_iata}")
def get_route_live_flights(dep_iata: str, arr_iata: str):
    """
    Returns live flights for a specific origin->destination route pair.
    Used in the Route Intelligence panel to show real aircraft on the selected path.
    """
    flights = fetch_route_flights(dep_iata.upper(), arr_iata.upper())
    return {"flights": flights, "route": f"{dep_iata.upper()}->{arr_iata.upper()}", "count": len(flights)}