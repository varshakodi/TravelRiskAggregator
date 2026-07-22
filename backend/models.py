from sqlalchemy import Column, Integer, String, Float
from geoalchemy2 import Geometry
from database import Base

class Airport(Base):
    __tablename__ = "airports"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    iata_code = Column(String, unique=True, index=True, nullable=False)
    location = Column(Geometry(geometry_type='POINT', srid=4326, spatial_index=True), nullable=False)
    risk_level = Column(String, nullable=False)  # "Low", "Medium", "High"
    risk_description = Column(String, nullable=True)
    severity_index = Column(Float, default=1.0)

class FlightEdge(Base):
    __tablename__ = "flight_edges"

    id = Column(Integer, primary_key=True, index=True)
    source_iata = Column(String, nullable=False)
    dest_iata = Column(String, nullable=False)
    base_distance_km = Column(Float, nullable=False)
    route_risk_modifier = Column(Float, default=0.0)

class DangerZone(Base):
    __tablename__ = "danger_zones"

    id = Column(Integer, primary_key=True, index=True)
    source_event = Column(String, nullable=False)
    description = Column(String, nullable=False)
    risk_level = Column(Integer, default=10)
    boundary = Column(Geometry(geometry_type='POLYGON', srid=4326, spatial_index=True), nullable=False)