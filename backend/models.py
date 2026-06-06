from sqlalchemy import Column, Integer, String
from geoalchemy2 import Geometry
from database import Base

class Airport(Base):
    __tablename__ = "airports"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    iata_code = Column(String, unique=True, index=True, nullable=False)
    location = Column(Geometry(geometry_type='POINT', srid=4326), nullable=False)
    
    # --- NEW RISK COLUMNS ---
    risk_level = Column(String, default="Low") # e.g., Low, Medium, High
    risk_description = Column(String, default="Clear skies and normal operations.")