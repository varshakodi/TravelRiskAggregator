import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler

from database import SessionLocal
from services.pathfinder import calculate_route_comparison
from services.ai_service import briefing_from_comparison
from workers.live_flights_worker import fetch_all_live_flights, fetch_route_flights
from workers.quake_worker import fetch_quakes
from workers.sigmet_worker import fetch_sigmets
from workers.zone_sweep import sweep_expired_zones

# Schema is owned by Alembic (`alembic upgrade head`) — the app no longer
# creates tables at import time.


@asynccontextmanager
async def lifespan(app: FastAPI):
    # -- startup: LIVE feeds (AWC SIGMETs + USGS quakes), safe to re-fire
    # because ingestion is idempotent (upserts keyed on external_id).
    # SIGMETs refresh often (typically 4h validity windows); quakes are a
    # daily-window feed; the sweep retires whatever has expired.
    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_sigmets, "interval", minutes=10)
    scheduler.add_job(fetch_quakes, "interval", minutes=15)
    scheduler.add_job(sweep_expired_zones, "interval", minutes=10)
    scheduler.start()
    print("[Engine] Live ingestion scheduled: AWC SIGMETs, USGS quakes, expiry sweep.")
    yield
    # -- shutdown: stop cleanly so no job is left mid-flight.
    scheduler.shutdown(wait=False)


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    # Only live zones: retired (is_active=false) and expired ones stay in the
    # table for history but never reach the map — matching what routing sees.
    query = text("""
        SELECT id, source_event, description, risk_level, ST_AsGeoJSON(boundary) as geojson
        FROM danger_zones
        WHERE is_active = true
          AND (expires_at IS NULL OR expires_at > NOW())
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
    # Clients send identifiers only; the server recomputes the route and owns
    # every fact that reaches the LLM prompt (prompt-injection hardening —
    # previously the client posted the route arrays back and we prompted
    # with them verbatim).
    origin: str
    destination: str

@app.post("/api/route/briefing")
def get_ai_briefing(req: BriefingRequest, db: Session = Depends(get_db)):
    comparison = calculate_route_comparison(db, req.origin, req.destination)
    if not comparison["standard_route"]:
        raise HTTPException(status_code=404, detail="No route exists between these airports.")
    return {"briefing": briefing_from_comparison(req.origin, req.destination, comparison)}


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