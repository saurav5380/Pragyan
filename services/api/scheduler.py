
'''
This is a scheduler which creates and re-creates the daily trading universe 
at 8:30AM, 9:30AM and 12:30PM IST
'''

# services/api/scheduler.py

from datetime import datetime
import pandas as pd
import time
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy import text
from app.db import SessionLocal
from services.api.app.services.universe import create_universe  # business logic lives here

IST = pytz.timezone("Asia/Kolkata")
scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
empty_df = pd.DataFrame()

def _label_asof_time(now_ist: datetime) -> str:
    hm = now_ist.strftime("%H:%M")
    if hm == "08:30":
        return "preopen"
    if hm == "09:30":
        return "0930"
    if hm == "12:30":
        return "1230"
    return now_ist.strftime("%H%M")  # fallback label if manually triggered

def daily_trade_universe():
    now_ist = datetime.now(IST)    # compute "now" at run time otherwise it gives a stale date
    asof_time = _label_asof_time(now_ist)                              

    try:
        trade_universe = create_universe()
        if trade_universe is None or trade_universe.empty:
            print("Universe is empty; skipping run")
            return empty_df

        # Build parameter list (one row per symbol)
        params = [
            {
                "date": now_ist.date(),                                # FIX: date only (IST)
                "asof_time": asof_time,                                # FIX: correct key name
                "symbol_id": int(row["symbol_id"]),
                "instrument_token": str(row["instrument_token"]),
                "atr_pct": float(row["atr_pct"]) if row["atr_pct"] is not None else None,
                "adv20": float(row["ADV20"]) if row["ADV20"] is not None else None,
                "score": float(row["score"]) if row["score"] is not None else None,
                "rank": int(row["rank"]) if row["rank"] is not None else None,
            }
            for _, row in trade_universe.iterrows()
        ]

        # Single transaction
        with SessionLocal() as db:
            db.execute(
                text(
                    """
                    INSERT INTO trading_universe
                      (date, asof_time, symbol_id, instrument_token, atr_pct, adv20, score, rank)
                    VALUES
                      (:date, :asof_time, :symbol_id, :instrument_token, :atr_pct, :adv20, :score, :rank)
                    ON CONFLICT (date, asof_time, symbol_id) DO UPDATE
                      SET instrument_token = EXCLUDED.instrument_token,
                          atr_pct          = EXCLUDED.atr_pct,
                          adv20            = EXCLUDED.adv20,
                          score            = EXCLUDED.score,
                          rank             = EXCLUDED.rank
                    """
                ),
                params,  # executemany with list[dict]
            )
            db.commit()

        print(f"Universe snapshot written: {len(params)} rows @ {now_ist} ({asof_time})")
        return trade_universe

    except Exception as e:
        print(f"[Universe job] Error: {e}")
        return empty_df

# Schedule: 08:30, 09:30, 12:30 IST
scheduler.add_job(daily_trade_universe, "cron", hour=8, minute=30, coalesce=True, max_instances=1)
scheduler.add_job(daily_trade_universe, "cron", hour=9, minute=30, coalesce=True, max_instances=1)
scheduler.add_job(daily_trade_universe, "cron", hour=12, minute=30, coalesce=True, max_instances=1)

print("Starting the scheduler")
scheduler.start()

try:
    while True:
        time.sleep(2)
except (KeyboardInterrupt, SystemExit):
    print("Shutting down scheduler")
    scheduler.shutdown()

