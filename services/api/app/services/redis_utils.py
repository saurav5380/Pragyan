import os
import datetime
import pytz  # CHANGE: ensure we use IST for "today"
import redis
import pandas as pd
from sqlalchemy import text  # CHANGE: parameterized SQL (safer/faster)
from app.db import SessionLocal
from fastapi import APIRouter

IST = pytz.timezone("Asia/Kolkata")

def write_universe_to_redis():
    """
    Publish *today's latest* trading-universe snapshot into Redis ZSET(s).

    Writes:
      - universe:YYYY-MM-DD   (dated copy, 36h TTL)
      - universe:latest       (pointer to latest set, 12h TTL)
    """

    # CHANGE: use IST "today" to match market day semantics
    today_ist = datetime.datetime.now(IST).date()
    today_str = today_ist.isoformat()

    # CHANGE: pick the latest asof_time for today (priority: 12:30 > 09:30 > preopen)
    pick_latest_asof_sql = text("""
        SELECT asof_time
        FROM trading_universe
        WHERE date = :d
        GROUP BY asof_time
        ORDER BY CASE asof_time
            WHEN '1230' THEN 3
            WHEN '0930' THEN 2
            WHEN 'preopen' THEN 1
            ELSE 0
        END DESC
        LIMIT 1
    """)

    # fetch only today's chosen snapshot rows 
    fetch_snapshot_sql = text("""
        SELECT date, asof_time, symbol_id, instrument_token, atr_pct, adv20, score, rank
        FROM trading_universe
        WHERE date = :d AND asof_time = :t
    """)

    # --- DB read (scoped session) ---
    with SessionLocal() as db:
        asof_row = db.execute(pick_latest_asof_sql, {"d": today_ist}).fetchone()
        if not asof_row:
            # CHANGE: no data for today; bail out cleanly
            return {"date": today_str, "asof_time": None, "wrote": 0}

        asof_time = asof_row[0]
        rows = db.execute(fetch_snapshot_sql, {"d": today_ist, "t": asof_time}).fetchall()

    # Put rows into a DataFrame 
    columns = ["date", "asof_time", "symbol_id", "instrument_token", "atr_pct", "adv20", "score", "rank"]
    universe_df = pd.DataFrame(rows, columns=columns)

    # --- Redis keys ---
    zkey_today = f"universe:{today_str}"
    zkey_latest = "universe:latest"  # live pointer

    # --- Redis client ---
    r = redis.Redis(
        host=os.environ.get("REDIS_HOST", "127.0.0.1"),
        port=int(os.environ.get("REDIS_PORT", 6379)),
        db=int(os.environ.get("REDIS_DB", 0)),
        password=os.environ.get("REDIS_PASSWORD"),
        decode_responses=True,  # CHANGE: read/write strings directly (no bytes decode hassle)
    )

    # CHANGE: build a single mapping for ZADD instead of per-row pipeline calls
    # (fewer roundtrips; also skip None scores safely)
    mapping = {}
    for _, row in universe_df.iterrows():
        token = str(row["instrument_token"]) if row["instrument_token"] is not None else str(row["symbol_id"])
        try:
            score = float(row["score"]) if row["score"] is not None else 0.0
        except Exception:
            score = 0.0
        mapping[token] = score

    pipe = r.pipeline(transaction=True)

    # CHANGE: always overwrite both keys atomically (delete before zadd)
    pipe.delete(zkey_today)
    pipe.delete(zkey_latest)

    if mapping:
        pipe.zadd(zkey_today, mapping=mapping)
        pipe.zadd(zkey_latest, mapping=mapping)

        # CHANGE: set TTLs after writing (no extra reads/copies)
        pipe.expire(zkey_today, 60 * 60 * 36)  # 36h
        pipe.expire(zkey_latest, 60 * 60 * 12)  # 12h

    pipe.execute()

    return {"date": today_str, "asof_time": asof_time, "wrote": len(mapping)}

router = APIRouter()

@router.post("/redis_zset")
def create_zset():
    write_universe_to_redis.delay()
    