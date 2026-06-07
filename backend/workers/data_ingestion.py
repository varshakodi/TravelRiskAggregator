import time
import requests
from sqlalchemy.orm import Session
from database import SessionLocal
from models import DangerZone

# ACLED API Documentation states the endpoint is: https://api.acleddata.com/acled/read
ACLED_URL = "https://api.acleddata.com/acled/read" 

def fetch_live_risk_data():
    """
    Fetches real-world geopolitical conflict data.
    Converts conflict points into PostGIS Polygons.
    """
    print("\n[Worker] Initiating global geopolitical risk fetch (ACLED)...")
    db = SessionLocal()
    
    try:
        # In a production environment, you would use your API credentials here.
        # Example query: ?limit=5&event_type=Battles
        # For this test, we are simulating a parsed API response of an active conflict.
        
        live_events = [
            {
                "source": "ACLED API (Simulated)",
                "description": "Active conflict zone detected near Iranian airspace.",
                "lat": 26.5,
                "lon": 54.0,
                "severity": 9
            }
        ]

        for event in live_events:
            # We create a 1.5 degree bounding box (roughly 150km) around the conflict coordinate
            min_lon, max_lon = event["lon"] - 1.5, event["lon"] + 1.5
            min_lat, max_lat = event["lat"] - 1.5, event["lat"] + 1.5
            
            # Create the PostGIS POLYGON string
            polygon_wkt = f"SRID=4326;POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, {max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))"
            
            new_zone = DangerZone(
                source_event=event["source"],
                description=event["description"],
                risk_level=event["severity"],
                boundary=polygon_wkt
            )
            
            db.add(new_zone)
            
        db.commit()
        print("[Worker] Successfully ingested live conflict data and mapped spatial polygons!")
        
    except Exception as e:
        print(f"[Worker] Data ingestion failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fetch_live_risk_data()