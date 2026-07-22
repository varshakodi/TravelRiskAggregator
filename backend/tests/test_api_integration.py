"""
Integration tests: the real FastAPI app against a real (disposable) PostGIS
database, migrated by the real Alembic migrations. Slower than units, and
worth it — they exercise the actual SQL, the geography cast, and the
constraints.
"""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["active_zones"] == 1  # only the active, unexpired test zone


def test_airports_lists_seeded_world(client):
    r = client.get("/api/airports")
    assert r.status_code == 200
    codes = {a["iata_code"] for a in r.json()["airports"]}
    assert codes == {"AAA", "BBB", "CCC", "DDD"}


def test_danger_zones_hides_inactive_and_expired(client):
    r = client.get("/api/danger-zones")
    assert r.status_code == 200
    zones = r.json()["zones"]
    assert len(zones) == 1
    assert "Active test zone" in zones[0]["description"]


def test_route_reroutes_around_active_zone(client):
    r = client.post("/api/route/calculate",
                    json={"origin": "AAA", "destination": "BBB"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "REROUTED"
    assert body["standard_route"]["path"] == ["AAA", "BBB"]
    # Detour must dodge the zone. CCC's corridor is clear; DDD's southern
    # detour is clear too (the southern box is INACTIVE) — either is valid,
    # what matters is the chosen path crosses nothing.
    assert body["safe_route"]["path"] != ["AAA", "BBB"]
    assert body["safe_route"]["zones_crossed"] == []
    # Threat matrix traces to the zone that blocked the corridor
    assert body["threat_breakdown"] == [
        {"category": "Geopolitical", "share_pct": 100, "severity_sum": 9}
    ]


def test_route_unknown_airport_404s(client):
    r = client.post("/api/route/calculate",
                    json={"origin": "AAA", "destination": "ZZZ"})
    assert r.status_code == 404


def test_briefing_takes_identifiers_only_and_uses_server_facts(client):
    r = client.post("/api/route/briefing",
                    json={"origin": "AAA", "destination": "BBB"})
    assert r.status_code == 200
    briefing = r.json()["briefing"]
    # No OPENAI_API_KEY in test env -> deterministic simulated fallback,
    # built from the server-computed reroute.
    assert briefing.startswith("[SIMULATED AI]")
    assert "AAA" in briefing and "BBB" in briefing


def test_fk_rejects_edge_to_nonexistent_airport(seeded):
    with pytest.raises(IntegrityError):
        with seeded.connect() as conn:
            conn.execute(text(
                "INSERT INTO flight_edges (source_iata, dest_iata, base_distance_km) "
                "VALUES ('XYZ', 'AAA', 1.0)"
            ))
            conn.commit()


def test_unique_constraint_rejects_duplicate_edge(seeded):
    with pytest.raises(IntegrityError):
        with seeded.connect() as conn:
            conn.execute(text(
                "INSERT INTO flight_edges (source_iata, dest_iata, base_distance_km) "
                "VALUES ('AAA', 'BBB', 445.0)"
            ))
            conn.commit()


def test_enum_rejects_invalid_risk_level(seeded):
    with pytest.raises(Exception) as exc_info:
        with seeded.connect() as conn:
            conn.execute(text(
                "INSERT INTO airports (name, iata_code, location, risk_level) VALUES "
                "('Bad', 'EEE', ST_GeomFromEWKT('SRID=4326;POINT(9 9)'), 'Lowish')"
            ))
            conn.commit()
    assert "airport_risk_level" in str(exc_info.value)
