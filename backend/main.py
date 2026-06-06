from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware  # <-- ADD THIS IMPORT
from sqlalchemy.orm import Session
from database import SessionLocal
from models import Airport

app = FastAPI()

# --- ADD THIS ENTIRE BLOCK ---
# Allow our React frontend to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite's default React port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# -----------------------------

# ... (your existing get_db and @app.get("/api/airports") code below)


from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from database import engine
from models import Base, Airport


@asynccontextmanager
async def lifespan(app: FastAPI):
    with engine.connect() as connection:
        connection.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        connection.commit()
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
def read_root():
    return {"message": "Hello, World!"}

from fastapi import Depends
from sqlalchemy.orm import Session
from database import SessionLocal # Assuming your SessionLocal is in database.py
from models import Airport

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/api/airports")
def get_all_airports(db: Session = Depends(get_db)):
    # Fetch all airports from Supabase
    airports = db.query(Airport).all()
    
    # Format the data to return as JSON
    results = []
    for airport in airports:
        results.append({
            "id": airport.id,
            "name": airport.name,
            "iata_code": airport.iata_code
            # We will handle the complex spatial 'location' conversion later!
        })
        
    return {"airports": results}
