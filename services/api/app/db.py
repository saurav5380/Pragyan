
from sqlalchemy import text
from ..db import engine, SessionLocal

def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def ping_db():
    with engine.connect as conn:
        conn.execute(text("SELECT 1"))
        