from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Create Base
Base = declarative_base()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:root@127.0.0.1:5433/pragyan")
engine = create_engine(DATABASE_URL, future=True, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()