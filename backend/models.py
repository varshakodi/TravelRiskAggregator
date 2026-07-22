from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from geoalchemy2 import Geometry
from database import Base


class Airport(Base):
    __tablename__ = "airports"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    iata_code = Column(String, unique=True, index=True, nullable=False)
    location = Column(Geometry(geometry_type='POINT', srid=4326, spatial_index=True), nullable=False)
    # Native Postgres enum: the DB itself rejects anything that isn't one of
    # these three values — free-text drift ("low", "LOW ", "Lowish") is impossible.
    risk_level = Column(Enum("Low", "Medium", "High", name="airport_risk_level"), nullable=False)
    risk_description = Column(String, nullable=True)
    severity_index = Column(Float, default=1.0)


class FlightEdge(Base):
    __tablename__ = "flight_edges"

    id = Column(Integer, primary_key=True, index=True)
    # Foreign keys: an edge may only reference airports that actually exist.
    # CASCADE: deleting an airport deletes its edges — no orphan references.
    source_iata = Column(String, ForeignKey("airports.iata_code", ondelete="CASCADE"), nullable=False)
    dest_iata = Column(String, ForeignKey("airports.iata_code", ondelete="CASCADE"), nullable=False)
    base_distance_km = Column(Float, nullable=False)

    # The same edge can't be inserted twice (it would silently double-count
    # in the routing graph).
    __table_args__ = (
        UniqueConstraint("source_iata", "dest_iata", name="uq_flight_edges_source_dest"),
    )


class DangerZone(Base):
    __tablename__ = "danger_zones"

    id = Column(Integer, primary_key=True, index=True)
    # The event's "passport number" from its source feed (e.g. a SIGMET id).
    # Unique, so ingesting the same event twice UPDATES the existing row
    # instead of inserting a twin — the key that makes ingestion idempotent.
    external_id = Column(String, unique=True, index=True, nullable=False)
    source_event = Column(String, nullable=False)
    description = Column(String, nullable=False)
    risk_level = Column(Integer, default=10)
    boundary = Column(Geometry(geometry_type='POLYGON', srid=4326, spatial_index=True), nullable=False)
    # Threats are events with a lifespan, not permanent map art.
    starts_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    # Soft off-switch: expired zones get deactivated (and kept for history),
    # and routing/display queries filter on this.
    is_active = Column(Boolean, nullable=False, server_default=text("true"))
