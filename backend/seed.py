import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from dotenv import load_dotenv

# 1. Load the database connection string from our .env file
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env file!")

# 2. Set up the connection engine
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
session = SessionLocal()

# Import our models directly
from models import Base, Airport

# Build the tables in Supabase if they don't exist
Base.metadata.create_all(bind=engine)

try:
    print("Connecting to Supabase and seeding airports...")
    
    # 3. Define our test airport data (Longitude, Latitude)
    airports_data = [
        {
            "name": "Kempegowda International Airport",
            "iata_code": "BLR",
            "lon": 77.7066,
            "lat": 13.1986
        },
        {
            "name": "Dubai International Airport",
            "iata_code": "DXB",
            "lon": 55.3657,
            "lat": 25.2532
        }
    ]

    # 4. Insert each airport if it doesn't already exist
    for data in airports_data:
        exists = session.query(Airport).filter(Airport.iata_code == data["iata_code"]).first()
        if not exists:
            # Create a spatial point geometry object using Shapely and GeoAlchemy2
            point_geom = from_shape(Point(data["lon"], data["lat"]), srid=4326)
            
            new_airport = Airport(
                name=data["name"],
                iata_code=data["iata_code"],
                location=point_geom  # THIS IS THE FIX: using 'location' instead of 'geometry'
            )
            session.add(new_airport)
            print(f"Added {data['iata_code']} to the database staging queue.")
        else:
            print(f"{data['iata_code']} already exists in database.")

    # Commit the changes to push them live to the cloud
    session.commit()
    print("Database seeding completed successfully!")

except Exception as e:
    session.rollback()
    print(f"An error occurred during seeding: {e}")
finally:
    session.close()