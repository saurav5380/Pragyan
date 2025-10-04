from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, text
from .settings import settings
from services.api.db import Base, engine, SessionLocal

# engine = create_engine(
#         settings.DATABASE_URL,
#         pool_pre_ping=True,
#         future=True
# )

# SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def ping_db():
    with engine.connect as conn:
        conn.execute(text("SELECT 1"))
        