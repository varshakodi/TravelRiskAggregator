"""
Aviation weather ingestion worker.

Data source is still SIMULATED (honestly labeled) — Phase 3 swaps in real
AWC SIGMET polygons. The mechanism is real: idempotent upsert keyed on
external_id, same pattern as data_ingestion.py (see the explanation there).
Weather cells get short validity windows — they expire in hours, not days.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy.dialects.postgresql import insert as pg_insert

from database import SessionLocal
from models import DangerZone
from workers.data_ingestion import _bbox_polygon_wkt


def fetch_aviation_weather_alerts():
    """Ingest severe-weather cells as danger zones (idempotently)."""
    print("[Telemetry] Aviation weather fetch (simulated feed)...")
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        weather_feeds = [
            {
                "external_id": "sim-awc:mediterranean-convective-001",
                "source": "AWC SIGMET (Simulated)",
                "description": "Severe Convective Cell - Flight Level FL340-FL410",
                "lat": 34.5,
                "lon": 22.0,
                "radius_deg": 2.0,
                "severity": 7,
                "valid_hours": 4,
            }
        ]

        for alert in weather_feeds:
            row = {
                "external_id": alert["external_id"],
                "source_event": alert["source"],
                "description": alert["description"],
                "risk_level": alert["severity"],
                "boundary": _bbox_polygon_wkt(alert["lon"], alert["lat"], alert["radius_deg"]),
                "starts_at": now,
                "expires_at": now + timedelta(hours=alert["valid_hours"]),
                "is_active": True,
            }
            stmt = pg_insert(DangerZone).values(**row).on_conflict_do_update(
                index_elements=["external_id"],
                set_={k: row[k] for k in
                      ("source_event", "description", "risk_level",
                       "boundary", "expires_at", "is_active")},
            )
            db.execute(stmt)

        db.commit()
        print(f"[Telemetry] Upserted {len(weather_feeds)} cell(s) — safe to re-run.")
    except Exception as e:
        print(f"[Telemetry] Weather ingestion failed: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    fetch_aviation_weather_alerts()
