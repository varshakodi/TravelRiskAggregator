from sqlalchemy import text
from database import engine

with engine.connect() as conn:
    res = conn.execute(text("SELECT routine_name FROM information_schema.routines WHERE routine_type='FUNCTION' AND specific_schema='public'")).fetchall()
    print("FUNCTIONS:", res)
