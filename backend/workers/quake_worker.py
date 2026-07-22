"""
LIVE feed: significant earthquakes (M4.5+, past day) from USGS.

Second adapter, same normalized output. Two things differ from SIGMETs and
are worth understanding:

  1. Quakes are POINTS (an epicenter), zones are POLYGONS — so we buffer
     each epicenter into a square whose size scales with magnitude. A M7
     event disrupts a far wider area (airport closures, ground operations,
     aftershock risk) than a M4.5.

  2. SIGMETs carry an official validity window; quakes don't. Here WE set
     the lifetime policy (24h from event time) — when the feed doesn't
     define expiry, the system must, or zones live forever.

USGS event ids (e.g. "us7000t2g0") are globally unique -> perfect external_id.
"""
from datetime import datetime, timedelta, timezone

import requests

from database import SessionLocal
from workers.zone_upsert import upsert_zone, ring_to_wkt

USGS_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson"
VALID_HOURS = 24


def _quake_zone_ring(lon: float, lat: float, mag: float):
    """Square around the epicenter; half-width grows with magnitude."""
    half = 0.5 + max(0.0, mag - 4.5) * 0.4   # M4.5 -> 0.5°, M7.0 -> 1.5°
    return [(lon - half, lat - half), (lon + half, lat - half),
            (lon + half, lat + half), (lon - half, lat + half)]


def fetch_quakes():
    """Ingest recent significant earthquakes as danger zones (idempotently)."""
    print("[USGS] Fetching M4.5+ earthquakes (past 24h)...")
    try:
        resp = requests.get(USGS_URL, timeout=15)
        resp.raise_for_status()
        features = resp.json().get("features", [])
    except Exception as e:
        print(f"[USGS] Fetch failed (feed unreachable, keeping existing zones): {e}")
        return

    db = SessionLocal()
    ingested = failed = 0
    try:
        for f in features:
            try:
                props = f.get("properties", {})
                lon, lat = f["geometry"]["coordinates"][:2]
                mag = props.get("mag") or 0.0
                event_time = datetime.fromtimestamp(props["time"] / 1000, tz=timezone.utc)

                upsert_zone(db, {
                    "external_id": f"usgs:{f['id']}",
                    "source_event": "USGS Seismic",
                    "description": f"M{mag:.1f} earthquake — {props.get('place', 'unknown location')}. "
                                   f"Ground operations may be disrupted.",
                    # severity tracks magnitude, clamped to our 1-10 scale
                    "risk_level": max(3, min(9, round(mag))),
                    "boundary": ring_to_wkt(_quake_zone_ring(lon, lat, mag)),
                    "starts_at": event_time,
                    "expires_at": event_time + timedelta(hours=VALID_HOURS),
                    "is_active": True,
                })
                ingested += 1
            except Exception as e:
                failed += 1
                print(f"[USGS] Skipping malformed record: {e}")

        db.commit()
        print(f"[USGS] Upserted {ingested} quake zones ({failed} malformed).")
    except Exception as e:
        print(f"[USGS] Batch failed: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    fetch_quakes()
