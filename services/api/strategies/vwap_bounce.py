from redis import Redis
import os 
from sqlalchemy import text
from services.api.app.db import SessionLocal
import pandas as pd

r = Redis(
        host=os.environ.get("REDIS_HOST", "127.0.0.1"),
        port=int(os.environ.get("REDIS_PORT", 6379)),
        db=int(os.environ.get("REDIS_DB", 0)),
        password=os.environ.get("REDIS_PASSWORD"),
        decode_responses=True,  # CHANGE: read/write strings directly (no bytes decode hassle)
    )

ZSET_Key = "universe:latest"

def vwap_bounce():
    focus_set = r.zrevrange(
        name=ZSET_Key,
        start=0,
        end=-1,
        withscores=True
    )
    sql_query = text("""SELECT symbol_id, symbol, vwap_dev, atr_pct
                     FROM features
                     WHERE symbol = :s """)
    #TODO: create SQL query and upsert into strategy_signals table for k_value > 1
    # upsert_into_strategy_signals = text(""" INSERT INTO strategy_signals""")
    columns = ["symbol_id", "symbol", "vwap_dev", "atr_pct"]
    with SessionLocal() as db:
        for stock, _ in focus_set:
            vwap_rows = db.execute(sql_query, {":s": stock}).fetchall()
        
        k_val = pd.Series([float(row["vwap_dev"]/row["atr_pct"]) for row in vwap_rows])

    vwap_df = pd.DataFrame(vwap_rows,columns)
    vwap_df["k_value"] = k_val
    vwap_bounce_df = vwap_df[vwap_df["k_value"] > 1.0]

    return vwap_bounce_df










