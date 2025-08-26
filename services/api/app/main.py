from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from .db import get_session, ping_db


app = FastAPI()

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.get("/dbcheck")
def db_check(db: Session = Depends(get_session)):
    db.execute(text("SELECT 1"))
    ext = db.execute(text("SELECT extname FROM pg_extension WHERE extname='timescaledb'")).fetchall()
    ht = db.execute(text("SELECT hypertable_name FROM timescaledb_information.hypertables WHERE hypertable_name='candles'")).fetchall()
    return{
        "db" : "ok",
        "timescaledb_version": bool(ext),
        "hypertable": bool(ht)
    }


