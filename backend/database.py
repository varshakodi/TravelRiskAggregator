import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

DATABASE_URL = os.environ["DATABASE_URL"]

# pool_pre_ping issues a cheap liveness check before handing out a pooled
# connection. The managed Postgres behind this app closes connections it
# considers idle, and the scheduler leaves the pool untouched for minutes
# at a time, so without the check a request can be handed a socket the
# server has already dropped and fail on the first statement.
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
