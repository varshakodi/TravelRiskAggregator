"""
Unit tests: pure logic, no database, no network — these run in milliseconds.

Graphs are built by hand in the exact adjacency shape _load_graph produces:
    {node: [(neighbor, base_dist, weighted_dist, zones_crossed), ...]}
"""
from services.pathfinder import _dijkstra, compute_threat_breakdown, derive_status
from services.cache import ttl_cache
from workers.quake_worker import _quake_zone_ring
from workers.sigmet_worker import HAZARD_SEVERITY
from workers.zone_upsert import ring_to_wkt

Z_WAR = {"source": "Test Geopolitical", "description": "war zone", "severity": 10}
Z_STORM = {"source": "Test SIGMET", "description": "storm", "severity": 7}


def _bidirectional(edges):
    """edges: {(a,b): (base, weighted, zones)} -> adjacency both ways."""
    graph = {}
    for (a, b), (base, weighted, zones) in edges.items():
        graph.setdefault(a, []).append((b, base, weighted, zones))
        graph.setdefault(b, []).append((a, base, weighted, zones))
    return graph


def test_clear_when_direct_path_crosses_nothing():
    graph = _bidirectional({
        ("A", "B"): (100, 100, []),
        ("A", "C"): (80, 80, []),
        ("C", "B"): (80, 80, []),
    })
    standard = _dijkstra(graph, "A", "B", ignore_risk=True)
    safe = _dijkstra(graph, "A", "B", ignore_risk=False)
    assert standard["path"] == safe["path"] == ["A", "B"]
    assert derive_status(standard, safe) == "CLEAR"


def test_rerouted_when_clean_detour_exists():
    graph = _bidirectional({
        ("A", "B"): (100, 100 * (1 + 100 * 10), [Z_WAR]),  # direct crosses war zone
        ("A", "C"): (80, 80, []),
        ("C", "B"): (80, 80, []),
    })
    standard = _dijkstra(graph, "A", "B", ignore_risk=True)
    safe = _dijkstra(graph, "A", "B", ignore_risk=False)
    assert standard["path"] == ["A", "B"]
    assert safe["path"] == ["A", "C", "B"]
    assert safe["zones_crossed"] == []
    assert derive_status(standard, safe) == "REROUTED"


def test_regression_phase1_bug_paths_differ_but_still_unsafe():
    """
    THE Phase 1 bug, encoded forever.

    Direct A-B crosses a severity-10 war zone; the only detour crosses a
    severity-7 storm. The two paths DIFFER — the old logic
    (`is_rerouted = standard != safe`) reported this as a successful
    reroute, i.e. a green "Route Clear" through a storm. The verdict must
    be NO_SAFE_PATH, because the winning path still crosses a zone.
    """
    graph = _bidirectional({
        ("A", "B"): (100, 100 * (1 + 100 * 10), [Z_WAR]),
        ("A", "C"): (80, 80 * (1 + 100 * 7), [Z_STORM]),
        ("C", "B"): (80, 80, []),
    })
    standard = _dijkstra(graph, "A", "B", ignore_risk=True)
    safe = _dijkstra(graph, "A", "B", ignore_risk=False)
    assert standard["path"] != safe["path"]          # the old logic's trap:
    assert safe["zones_crossed"] == [Z_STORM]        # ...paths differ, yet unsafe
    assert derive_status(standard, safe) == "NO_SAFE_PATH"


def test_unreachable_destination_returns_none():
    graph = _bidirectional({("A", "B"): (100, 100, [])})
    assert _dijkstra(graph, "A", "ZZZ", ignore_risk=False) is None


def test_threat_breakdown_normalizes_and_sorts():
    zones = [Z_WAR, Z_STORM, dict(Z_STORM)]  # 10 geopolitical, 14 weather
    breakdown = compute_threat_breakdown(zones)
    assert [b["category"] for b in breakdown] == ["Aviation Weather", "Geopolitical"]
    assert sum(b["share_pct"] for b in breakdown) in (99, 100, 101)  # rounding
    assert breakdown[0]["severity_sum"] == 14


def test_threat_breakdown_empty_when_no_zones():
    assert compute_threat_breakdown([]) == []


def test_ttl_cache_expires(monkeypatch):
    import services.cache as cache_mod
    clock = {"t": 1000.0}
    monkeypatch.setattr(cache_mod.time, "monotonic", lambda: clock["t"])

    calls = {"n": 0}

    @ttl_cache(seconds=30)
    def fn():
        calls["n"] += 1
        return calls["n"]

    assert fn() == 1
    assert fn() == 1          # within TTL: cached
    clock["t"] += 31
    assert fn() == 2          # TTL elapsed: recomputed


def test_quake_ring_scales_with_magnitude():
    small = _quake_zone_ring(0, 0, 4.5)
    big = _quake_zone_ring(0, 0, 7.0)
    assert small[0] == (-0.5, -0.5)
    assert big[0] == (-1.5, -1.5)


def test_hazard_severity_ranks_flight_critical_hazards_highest():
    assert HAZARD_SEVERITY["VA"] == HAZARD_SEVERITY["TC"] == 9
    assert HAZARD_SEVERITY["TS"] < HAZARD_SEVERITY["VA"]


def test_ring_to_wkt_closes_the_ring():
    wkt = ring_to_wkt([(0, 0), (1, 0), (1, 1)])
    assert wkt.startswith("SRID=4326;POLYGON((")
    assert wkt.count("0 0") == 2  # first point repeated at the end
