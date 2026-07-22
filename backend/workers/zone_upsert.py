"""
Shared write-path for all zone ingestion workers.

Every feed adapter (SIGMET, USGS quakes, ...) normalizes its records into the
same dict shape and hands them here. One idempotent upsert implementation,
keyed on external_id — re-ingesting an event updates the existing row in
place (and re-activates it if the sweep had retired it) instead of creating
a duplicate. See Phase 2's workers for the full at-least-once-delivery story.
"""
from sqlalchemy.dialects.postgresql import insert as pg_insert

from models import DangerZone

# Fields refreshed when an event we already know about is re-ingested.
_UPDATABLE = ("source_event", "description", "risk_level",
              "boundary", "starts_at", "expires_at", "is_active")


def upsert_zone(db, row: dict) -> None:
    """row must contain external_id + the _UPDATABLE fields above."""
    stmt = pg_insert(DangerZone).values(**row).on_conflict_do_update(
        index_elements=["external_id"],
        set_={k: row[k] for k in _UPDATABLE},
    )
    db.execute(stmt)


def ring_to_wkt(points: list[tuple[float, float]]) -> str:
    """(lon, lat) list -> closed SRID-tagged POLYGON WKT."""
    if points[0] != points[-1]:
        points = points + [points[0]]
    body = ", ".join(f"{lon} {lat}" for lon, lat in points)
    return f"SRID=4326;POLYGON(({body}))"
