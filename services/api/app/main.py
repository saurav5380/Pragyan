from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from .db import get_session
from .routes.kite_callback import router as kite_callback_router
import os 
from dotenv import load_dotenv
from contextlib import asynccontextmanager
from services.api.scheduler import start_scheduler, shutdown_scheduler
from services.api.app.workers.tasks import router as trade_pipeline

load_dotenv()

app = FastAPI()
API_KEY = os.environ.get("KITE_API_KEY")

@app.get("/", response_class=HTMLResponse)
def welcome():
    return HTMLResponse(f"<h3><a href='https://kite.trade/connect/login?v=3&api_key={API_KEY}'>Login to Kite</a></h3>")

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

app.include_router(kite_callback_router)

@asynccontextmanager
async def lifespan(app:FastAPI):
    start_scheduler()
    yield
    shutdown_scheduler()

app = FastAPI(lifespan=lifespan)

app.include_router(trade_pipeline)




