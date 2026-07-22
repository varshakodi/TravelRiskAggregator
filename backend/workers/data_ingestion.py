"""
Geopolitical risk ingestion worker.

Data source is still SIMULATED (a hardcoded event, honestly labeled) — Phase 3
swaps in a real feed. What's real as of Phase 2 is the ingestion MECHANISM:

  Idempotent upsert. Schedulers double-fire and feeds re-send events
  (at-least-once delivery), so a worker must be safe to run any number of
  times. Every event carries a stable external_id, and we write it with
  INSERT ... ON CONFLICT (external_id) DO UPDATE — "insert this event, and
  if a row with this id already exists, update that row instead." Running
  this 100 times produces exactly one row per event, not 100 copies.
  (The old version did a plain INSERT per run — duplicates piled up forever,
  which is why the scheduler had to be disabled.)
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy.dialects.postgresql import insert as pg_insert

from database import SessionLocal
from models import DangerZone


def _bbox_polygon_wkt(lon: float, lat: float, half_deg: float) -> str:
    """Square polygon (WKT) centered on a coordinate, ~half_deg° in each direction."""
    min_lon, max_lon = lon - half_deg, lon + half_deg
    min_lat, max_lat = lat - half_deg, lat + half_deg
    return (
        f"SRID=4326;POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, "
        f"{max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))"
    )


def fetch_live_risk_data():
    """Ingest geopolitical conflict events as danger zones (idempotently)."""
    print("[Worker] Geopolitical risk fetch (simulated feed)...")
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        # Simulated parsed-API response. Phase 3 replaces this list with real
        # events; each real event will carry a real id from its source.
        live_events = [
            {
                "external_id": "sim-acled:persian-gulf-conflict-001",
                "source": "ACLED (Simulated)",
                "description": "Active conflict zone detected near Iranian airspace.",
                # Hugs the Iranian coastline (as the description says) without
                # swallowing DXB at lat 25.25 — the box spans lat 26.5–29.5.
                "lat": 28.0,
                "lon": 54.0,
                "severity": 9,
                "valid_hours": 24,
            }
        ]

        for event in live_events:
            row = {
                "external_id": event["external_id"],
                "source_event": event["source"],
                "description": event["description"],
                "risk_level": event["severity"],
                "boundary": _bbox_polygon_wkt(event["lon"], event["lat"], 1.5),
                "starts_at": now,
                "expires_at": now + timedelta(hours=event["valid_hours"]),
                "is_active": True,
            }
            stmt = pg_insert(DangerZone).values(**row).on_conflict_do_update(
                index_elements=["external_id"],
                # On re-ingest: refresh the event's details and extend its
                # validity window; re-activate it if the sweep had retired it.
                set_={k: row[k] for k in
                      ("source_event", "description", "risk_level",
                       "boundary", "expires_at", "is_active")},
            )
            db.execute(stmt)

        db.commit()
        print(f"[Worker] Upserted {len(live_events)} event(s) — safe to re-run.")
    except Exception as e:
        print(f"[Worker] Ingestion failed: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    fetch_live_risk_data()
