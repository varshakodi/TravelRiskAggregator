"""
Shared pytest setup.

Key trick: DATABASE_URL is pointed at a disposable test database BEFORE any
app module is imported (database.py reads the env at import time). Tests
never touch the real dev database.

The test DB is built from the same Alembic migrations production uses —
so the tests also prove the migrations themselves run clean from scratch.
"""
import os
import subprocess
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]

# Must happen before importing database/models/main anywhere in the test run.
TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://localhost:5432/risk_aggregator_test",
)
os.environ["DATABASE_URL"] = TEST_DB_URL

import pytest  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def test_database():
    """Create (if needed), migrate, and hand back the disposable test DB."""
    # Local convenience: create the DB if it doesn't exist. In CI the
    # postgis service container pre-creates it (and the postgis extension).
    admin_url = TEST_DB_URL.rsplit("/", 1)[0] + "/postgres"
    db_name = TEST_DB_URL.rsplit("/", 1)[1]
    admin = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with admin.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": db_name}
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    finally:
        admin.dispose()

    engine = create_engine(TEST_DB_URL)
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.commit()

    # Same migrations as production — this is also a test OF the migrations.
    subprocess.run(
        [str(BACKEND_DIR / "venv" / "bin" / "alembic")
         if (BACKEND_DIR / "venv").exists() else "alembic",
         "upgrade", "head"],
        cwd=BACKEND_DIR,
        env={**os.environ, "DATABASE_URL": TEST_DB_URL},
        check=True,
        capture_output=True,
    )
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def seeded(test_database):
    r"""
    A tiny deterministic world: a diamond of 4 airports where the direct
    A->B leg crosses an active zone but the A->C->B detour is clear, plus
    one INACTIVE and one EXPIRED zone to prove the lifecycle filters.

        C (2,3)
       /  \
    A(0,0)--B(4,0)   direct path crosses ZONE (lon 1..3, lat -0.5..0.5)
       \  /
        D (2,-3)
    """
    with test_database.connect() as conn:
        conn.execute(text("DELETE FROM flight_edges"))
        conn.execute(text("DELETE FROM danger_zones"))
        conn.execute(text("DELETE FROM airports"))

        conn.execute(text("""
            INSERT INTO airports (name, iata_code, location, risk_level, risk_description, severity_index) VALUES
            ('Alpha',   'AAA', ST_GeomFromEWKT('SRID=4326;POINT(0 0)'),  'Low', 'test', 1.0),
            ('Bravo',   'BBB', ST_GeomFromEWKT('SRID=4326;POINT(4 0)'),  'Low', 'test', 1.0),
            ('Charlie', 'CCC', ST_GeomFromEWKT('SRID=4326;POINT(2 3)'),  'Low', 'test', 1.0),
            ('Delta',   'DDD', ST_GeomFromEWKT('SRID=4326;POINT(2 -3)'), 'Low', 'test', 1.0)
        """))
        conn.execute(text("""
            INSERT INTO flight_edges (source_iata, dest_iata, base_distance_km) VALUES
            ('AAA', 'BBB', 445.0),
            ('AAA', 'CCC', 400.0),
            ('CCC', 'BBB', 400.0),
            ('AAA', 'DDD', 400.0),
            ('DDD', 'BBB', 400.0)
        """))
        conn.execute(text("""
            INSERT INTO danger_zones (external_id, source_event, description, risk_level, boundary, is_active, expires_at) VALUES
            ('test:active-box', 'Test Geopolitical', 'Active test zone on the direct corridor', 9,
             ST_GeomFromEWKT('SRID=4326;POLYGON((1 -0.5, 3 -0.5, 3 0.5, 1 0.5, 1 -0.5))'), true, NULL),
            ('test:inactive-box', 'Test Geopolitical', 'Deactivated zone (must be invisible)', 9,
             ST_GeomFromEWKT('SRID=4326;POLYGON((1 -4, 3 -4, 3 -2, 1 -2, 1 -4))'), false, NULL),
            ('test:expired-box', 'Test Weather', 'Expired zone (must be invisible)', 8,
             ST_GeomFromEWKT('SRID=4326;POLYGON((1 2, 3 2, 3 4, 1 4, 1 2))'), true, NOW() - INTERVAL '1 hour')
        """))
        conn.commit()
    return test_database


@pytest.fixture()
def client(seeded):
    """FastAPI TestClient against the seeded test DB. Instantiated without
    a `with` block on purpose: the lifespan (and thus the APScheduler jobs)
    never starts during tests."""
    from fastapi.testclient import TestClient
    from main import app
    return TestClient(app)
