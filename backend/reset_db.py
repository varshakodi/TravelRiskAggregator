from database import engine
from models import Base

print("Connecting to the database...")
# This tells SQLAlchemy to look at your models and delete the corresponding tables
Base.metadata.drop_all(bind=engine)
print("Success! Old tables have been dropped.")