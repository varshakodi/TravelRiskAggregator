import heapq
from sqlalchemy.orm import Session
from shapely.wkb import loads
from shapely.geometry import LineString
from models import FlightEdge, Airport, DangerZone

def run_dijkstra(db: Session, origin_iata: str, dest_iata: str, ignore_risk: bool = False):
    edges = db.query(FlightEdge).all()
    
    # Load airports into a dict of {iata_code: shapely.geometry.Point}
    # and danger zones into a list of shapely.geometry.Polygon
    airports = {a.iata_code: loads(bytes(a.location.data)) for a in db.query(Airport).all()}
    danger_zones = [loads(bytes(dz.boundary.data)) for dz in db.query(DangerZone).all()]

    graph = {}
    
    for edge in edges:
        if edge.source_iata not in graph: graph[edge.source_iata] = []
        if edge.dest_iata not in graph: graph[edge.dest_iata] = []
        
        # Calculate dynamic spatial intersection risk
        intersection_penalty = 0.0
        if not ignore_risk and edge.source_iata in airports and edge.dest_iata in airports:
            pt1 = airports[edge.source_iata]
            pt2 = airports[edge.dest_iata]
            line = LineString([pt1, pt2])
            for dz in danger_zones:
                if line.intersects(dz):
                    intersection_penalty += 10000.0  # Massive penalty for crossing a danger zone

        penalty_weight = edge.base_distance_km if ignore_risk else edge.base_distance_km + (edge.route_risk_modifier * 1000.0) + intersection_penalty
        
        graph[edge.source_iata].append((edge.dest_iata, penalty_weight, edge.base_distance_km))
        graph[edge.dest_iata].append((edge.source_iata, penalty_weight, edge.base_distance_km))
    
    queue = [(0.0, origin_iata, [origin_iata], 0.0)]
    seen = set()
    
    while queue:
        weighted_cost, node, path, actual_dist = heapq.heappop(queue)
        if node in seen: continue
        seen.add(node)
        
        if node == dest_iata:
            return {"path": path, "total_distance_km": round(actual_dist, 2)}
            
        for next_node, penalty_cost, base_dist in graph.get(node, []):
            if next_node not in seen:
                heapq.heappush(queue, (weighted_cost + penalty_cost, next_node, path + [next_node], actual_dist + base_dist))
    return None

def calculate_route_comparison(db: Session, origin_iata: str, dest_iata: str):
    standard_route = run_dijkstra(db, origin_iata, dest_iata, ignore_risk=True)
    safe_route = run_dijkstra(db, origin_iata, dest_iata, ignore_risk=False)
    
    return {
        "standard_route": standard_route,
        "safe_route": safe_route,
        "is_rerouted": standard_route != safe_route if standard_route and safe_route else False
    }