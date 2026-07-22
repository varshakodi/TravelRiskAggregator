"""
LIVE feed: international SIGMETs from the Aviation Weather Center.

SIGMET = Significant Meteorological Information — the official hazard
advisories pilots actually route around (thunderstorms, severe turbulence,
volcanic ash, icing, tropical cyclones). They arrive as real polygons with
official validity windows: exactly our DangerZone shape, published by
meteorologists. Free, no API key.

This module is an ADAPTER: it translates AWC's record shape into the one
normalized zone dict that zone_upsert.upsert_zone() writes. Defensive rules:
  - one malformed record never kills the batch (per-record try/except)
  - expires_at comes from THEIR validTimeTo, not our guess; records already
    expired at fetch time are skipped
  - records without a usable polygon (<3 points) are skipped and counted

Known limitation: polygons spanning the antimeridian (lon ±180) are stored
as-is and may render/intersect oddly; acceptable for now and noted honestly.
"""
from datetime import datetime, timezone

import requests

from database import SessionLocal
from workers.zone_upsert import upsert_zone, ring_to_wkt

ISIGMET_URL = "https://aviationweather.gov/api/data/isigmet?format=json"

# Encoding aviation domain knowledge as data: how dangerous is each hazard
# class to a flight? Volcanic ash and tropical cyclones are flight-critical;
# mountain wave is comparatively localized.
HAZARD_SEVERITY = {
    "TC": 9,    # tropical cyclone
    "VA": 9,    # volcanic ash — destroys jet engines
    "TS": 7,    # thunderstorm
    "ICE": 6,   # severe icing
    "TURB": 5,  # severe turbulence
    "MTW": 4,   # mountain wave
}
DEFAULT_SEVERITY = 5

HAZARD_NAMES = {
    "TC": "Tropical cyclone", "VA": "Volcanic ash", "TS": "Thunderstorms",
    "ICE": "Severe icing", "TURB": "Severe turbulence", "MTW": "Mountain wave",
}


def fetch_sigmets():
    """Ingest current international SIGMET polygons (idempotently)."""
    print("[SIGMET] Fetching live international SIGMETs...")
    try:
        resp = requests.get(ISIGMET_URL, timeout=15)
        resp.raise_for_status()
        records = resp.json()
    except Exception as e:
        print(f"[SIGMET] Fetch failed (feed unreachable, keeping existing zones): {e}")
        return

    now = datetime.now(timezone.utc)
    db = SessionLocal()
    ingested = skipped = failed = 0
    try:
        for rec in records:
            try:
                coords = rec.get("coords") or []
                valid_to = rec.get("validTimeTo")
                if len(coords) < 3 or not valid_to:
                    skipped += 1
                    continue
                expires_at = datetime.fromtimestamp(valid_to, tz=timezone.utc)
                if expires_at <= now:
                    skipped += 1  # already expired at fetch time
                    continue

                hazard = rec.get("hazard") or "UNKNOWN"
                fir = rec.get("firName") or rec.get("firId") or "Unknown FIR"
                qualifier = rec.get("qualifier") or ""
                series = rec.get("seriesId") or "?"
                valid_from = rec.get("validTimeFrom")

                # firId+series recycle daily; adding validTimeFrom makes each
                # issuance a distinct event identity.
                external_id = f"awc:{rec.get('firId', '?')}:{series}:{valid_from}"

                hazard_name = HAZARD_NAMES.get(hazard, hazard)
                desc = f"{hazard_name} ({qualifier}) — {fir}".replace("() — ", "— ")

                upsert_zone(db, {
                    "external_id": external_id,
                    "source_event": "AWC SIGMET",
                    "description": desc,
                    "risk_level": HAZARD_SEVERITY.get(hazard, DEFAULT_SEVERITY),
                    "boundary": ring_to_wkt([(p["lon"], p["lat"]) for p in coords]),
                    "starts_at": datetime.fromtimestamp(valid_from, tz=timezone.utc) if valid_from else now,
                    "expires_at": expires_at,
                    "is_active": True,
                })
                ingested += 1
            except Exception as e:
                failed += 1
                print(f"[SIGMET] Skipping malformed record: {e}")

        db.commit()
        print(f"[SIGMET] Upserted {ingested} zones "
              f"(skipped {skipped} expired/no-polygon, {failed} malformed).")
    except Exception as e:
        print(f"[SIGMET] Batch failed: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    fetch_sigmets()
