import json
from database import SessionLocal
from services.pathfinder import calculate_route_comparison

db = SessionLocal()
res = calculate_route_comparison(db, "HND", "BLR")
print("REROUTED:", res["is_rerouted"])
print("STANDARD PATH:", res["standard_route"]["path"])
print("SAFE PATH:", res["safe_route"]["path"])
