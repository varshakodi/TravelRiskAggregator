import heapq
from sqlalchemy.orm import Session
from models import FlightEdge, Airport

def calculate_optimal_route(db: Session, origin_iata: str, dest_iata: str):
    # Fetch all flight segments from the database
    edges = db.query(FlightEdge).all()
    
    # 1. Build the Adjacency List Graph
    graph = {}
    for edge in edges:
        if edge.source_iata not in graph:
            graph[edge.source_iata] = []
        if edge.dest_iata not in graph:
            graph[edge.dest_iata] = []
        
        # Algorithmic Cost calculation:
        # Dangerous paths receive a heavy distance penalty so Dijkstra avoids them
        penalty_weight = edge.base_distance_km + (edge.route_risk_modifier * 1000.0)
        
        graph[edge.source_iata].append((edge.dest_iata, penalty_weight, edge.base_distance_km))
        graph[edge.dest_iata].append((edge.source_iata, penalty_weight, edge.base_distance_km))
    
    # 2. Execute Dijkstra's Algorithm
    # Priority Queue stores tuple: (total_weighted_cost, current_node, path_history, true_distance_km)
    queue = [(0.0, origin_iata, [origin_iata], 0.0)]
    seen = set()
    
    while queue:
        weighted_cost, node, path, actual_distance = heapq.heappop(queue)
        
        if node in seen:
            continue
        seen.add(node)
        
        # Target node acquired
        if node == dest_iata:
            return {
                "path": path, 
                "total_distance_km": round(actual_distance, 2)
            }
        
        for next_node, penalty_cost, base_dist in graph.get(node, []):
            if next_node in seen:
                continue
                
            heapq.heappush(queue, (
                weighted_cost + penalty_cost,
                next_node,
                path + [next_node],
                actual_distance + base_dist
            ))
            
    return None