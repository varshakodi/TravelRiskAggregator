import heapq

from sqlalchemy import text
from sqlalchemy.orm import Session

# Multiplier applied per unit of summed zone risk_level. Chosen so that even
# the lowest-severity seeded zone (risk_level=8) makes an edge more expensive
# than any real detour in this graph (edges: ~300-6500km, worst-case full
# detour: ~20,000km) — i.e. Dijkstra always prefers a clear detour when one
# exists, and only ranks by severity when forced to pick among unsafe options.
RISK_LAMBDA = 100

# One query replaces three (edges / airports / zones) plus the old O(edges x
# zones) Shapely loop. The ::geography cast is the correctness fix: it makes
# ST_Intersects treat the segment between two airports as a geodesic arc
# (the real flight path), instead of a straight line in raw lon/lat space,
# which is what both the old Shapely LineString and a plain ::geometry
# comparison do. FILTER excludes the LEFT JOIN's null row so a
# non-intersecting edge gets zone_risk=0 and zones_crossed=[], not [NULL].
EDGE_QUERY = text("""
    SELECT
        fe.source_iata,
        fe.dest_iata,
        fe.base_distance_km,
        COALESCE(SUM(dz.risk_level), 0) AS zone_risk,
        COALESCE(
            json_agg(json_build_object(
                'source', dz.source_event,
                'description', dz.description,
                'severity', dz.risk_level
            )) FILTER (WHERE dz.id IS NOT NULL),
            '[]'
        ) AS zones_crossed
    FROM flight_edges fe
    JOIN airports a1 ON a1.iata_code = fe.source_iata
    JOIN airports a2 ON a2.iata_code = fe.dest_iata
    LEFT JOIN danger_zones dz
        ON ST_Intersects(
            ST_MakeLine(a1.location, a2.location)::geography,
            dz.boundary::geography
        )
        -- Lifecycle filter lives in the ON clause, NOT in a WHERE: filtering
        -- a left-joined table's columns in WHERE silently drops the rows
        -- where the zone side is NULL — i.e. every SAFE edge — turning the
        -- LEFT JOIN into an inner join. In ON, it only limits which zones
        -- attach to an edge; edges themselves always survive.
        AND dz.is_active = true
        AND (dz.expires_at IS NULL OR dz.expires_at > NOW())
    GROUP BY fe.id, fe.source_iata, fe.dest_iata, fe.base_distance_km
""")


def _load_graph(db: Session):
    """Fetch every edge once, pre-annotated with which zones it crosses."""
    rows = db.execute(EDGE_QUERY).fetchall()
    graph = {}
    for r in rows:
        weighted_km = r.base_distance_km * (1 + RISK_LAMBDA * r.zone_risk)
        forward = (r.dest_iata, r.base_distance_km, weighted_km, r.zones_crossed)
        backward = (r.source_iata, r.base_distance_km, weighted_km, r.zones_crossed)
        graph.setdefault(r.source_iata, []).append(forward)
        graph.setdefault(r.dest_iata, []).append(backward)
    return graph


def _dijkstra(graph, origin_iata: str, dest_iata: str, ignore_risk: bool):
    # (cost, node, path, actual_dist, zones_crossed) — same lazy-deletion
    # Dijkstra as before; each popped state now also carries the union of
    # zones crossed to reach it, so the winner's zones_crossed is known
    # the moment we pop the destination, with no separate re-walk needed.
    queue = [(0.0, origin_iata, [origin_iata], 0.0, [])]
    seen = set()

    while queue:
        cost, node, path, actual_dist, zones_hit = heapq.heappop(queue)
        if node in seen:
            continue
        seen.add(node)

        if node == dest_iata:
            return {
                "path": path,
                "total_distance_km": round(actual_dist, 2),
                "zones_crossed": zones_hit,
            }

        for next_node, base_dist, weighted_km, edge_zones in graph.get(node, []):
            if next_node in seen:
                continue
            step_cost = base_dist if ignore_risk else weighted_km
            new_zones = zones_hit + [z for z in edge_zones if z not in zones_hit]
            heapq.heappush(
                queue,
                (cost + step_cost, next_node, path + [next_node], actual_dist + base_dist, new_zones),
            )
    return None


def calculate_route_comparison(db: Session, origin_iata: str, dest_iata: str):
    graph = _load_graph(db)
    standard_route = _dijkstra(graph, origin_iata, dest_iata, ignore_risk=True)
    safe_route = _dijkstra(graph, origin_iata, dest_iata, ignore_risk=False)

    if not standard_route or not safe_route:
        # Both runs traverse the same graph edges (just different weights),
        # so if one is unreachable, so is the other — this is "no route
        # exists in the network," a connectivity fact the caller already
        # 404s on. NOT the same thing as NO_SAFE_PATH, which means a route
        # exists but every option crosses a zone — mislabeling this as
        # NO_SAFE_PATH would conflate a graph-topology gap with a real
        # safety failure.
        return {
            "standard_route": standard_route,
            "safe_route": safe_route,
            "status": None,
            "zones_crossed": [],
        }

    status = derive_status(standard_route, safe_route)
    zones_crossed = safe_route["zones_crossed"]

    return {
        "standard_route": standard_route,
        "safe_route": safe_route,
        "status": status,
        "zones_crossed": zones_crossed,
        # The threats relevant to this corridor = whatever the DIRECT path
        # crosses (that's what forced a reroute, or would have).
        "threat_breakdown": compute_threat_breakdown(standard_route["zones_crossed"]),
    }


def derive_status(standard_route: dict, safe_route: dict) -> str:
    """
    The safety verdict. Pure function (no DB) so it's unit-testable.

    This is the Phase 1 bug fix, isolated: status comes from what the
    winning path ACTUALLY CROSSES, never from whether the two paths differ.
    (The old logic inferred "safe alternative found" from path inequality —
    when every option crossed a zone, it reported a green Route Clear
    through active threat airspace.)
    """
    if safe_route["zones_crossed"]:
        return "NO_SAFE_PATH"
    if standard_route["path"] == safe_route["path"]:
        return "CLEAR"
    return "REROUTED"


# Source feed -> display category. New feeds slot in here.
_CATEGORY_BY_SOURCE = [
    ("Geopolitical", "Geopolitical"),
    ("SIGMET", "Aviation Weather"),
    ("Weather", "Aviation Weather"),
    ("Seismic", "Seismic"),
]


def compute_threat_breakdown(zones: list) -> list:
    """
    Per-corridor threat composition, replacing the UI's old hardcoded
    percentages: group the corridor's zones by category, weight by severity,
    normalize to shares of 100. Every number traces back to actual zones.
    """
    totals: dict = {}
    for z in zones:
        source = z.get("source", "")
        category = next((cat for key, cat in _CATEGORY_BY_SOURCE if key in source), "Other")
        totals[category] = totals.get(category, 0) + (z.get("severity") or 0)

    grand_total = sum(totals.values())
    if not grand_total:
        return []
    return [
        {"category": cat, "share_pct": round(100 * sev / grand_total), "severity_sum": sev}
        for cat, sev in sorted(totals.items(), key=lambda kv: -kv[1])
    ]
