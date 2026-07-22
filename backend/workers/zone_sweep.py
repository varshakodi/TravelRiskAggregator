"""
Zone expiry sweep — the janitor job.

Ingestion workers bring zones in; this retires them once their expires_at
passes. Soft-delete (is_active=false) rather than DELETE: the row is kept
for history, and if the same event re-appears in a feed, the upsert simply
re-activates it. Routing and the map only look at active, unexpired zones.

Also idempotent by nature: sweeping twice retires nothing extra.
"""
from sqlalchemy import text

from database import SessionLocal


def sweep_expired_zones():
    db = SessionLocal()
    try:
        result = db.execute(text("""
            UPDATE danger_zones
            SET is_active = false
            WHERE is_active = true
              AND expires_at IS NOT NULL
              AND expires_at < NOW()
        """))
        db.commit()
        if result.rowcount:
            print(f"[Sweep] Retired {result.rowcount} expired zone(s).")
    except Exception as e:
        print(f"[Sweep] Failed: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    sweep_expired_zones()
