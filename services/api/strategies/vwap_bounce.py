from redis import Redis
import os 
from sqlalchemy import text
from services.api.app.db import SessionLocal
import pandas as pd
import datetime
import pytz

#contants
IST = pytz.timezone("Asia/Kolkata")
ZSET_Key = "universe:latest"
current_time_ist = datetime.datetime.now(IST)
current_date = current_time_ist.date()

r = Redis(
        host=os.environ.get("REDIS_HOST", "127.0.0.1"),
        port=int(os.environ.get("REDIS_PORT", 6379)),
        db=int(os.environ.get("REDIS_DB", 0)),
        password=os.environ.get("REDIS_PASSWORD"),
        decode_responses=True,  # CHANGE: read/write strings directly (no bytes decode hassle)
    )



def vwap_bounce():
    focus_set = r.zrevrange(
        name=ZSET_Key,
        start=0,
        end=-1,
        withscores=True
    )

    # extract the names of stocks in the focus set 
    focus_stocks = [stock for stock, _ in focus_set]

    # Inputs:
        # :symbol_ids  (int[])
        # :trade_date  (date)
    sql_query = text("""
        WITH preferred_asof AS (
        SELECT asof_time
        FROM trading_universe
        WHERE date = :trade_date
        GROUP BY asof_time
        ORDER BY
            CASE asof_time
            WHEN '1230'    THEN 3
            WHEN '0930'    THEN 2
            WHEN 'preopen' THEN 1
            ELSE 0
            END DESC
        LIMIT 1
        ),
        latest_feats AS (
        SELECT DISTINCT ON (f.symbol_id)
                f.symbol_id,
                f.ts,
                f.vwap,
                f.vwap_dev,           
                f.atr_pct,            
                f.rsi14,
                f.vol_z
        FROM features AS f
        WHERE f.symbol_id = ANY(:symbol_ids)
            AND ((f.ts AT TIME ZONE 'Asia/Kolkata')::date = :trade_date)
        ORDER BY f.symbol_id, f.ts DESC
        )
        SELECT
        lf.symbol_id,
        lf.ts,
        lf.vwap,
        lf.vwap_dev,               
        lf.atr_pct,  
        lf.rsi14,
        lf.vol_z,
        tu.score     AS universe_score,
        tu.rank      AS universe_rank,
        tu.adv20,
        tu.atr_pct   AS daily_atr_pct
        FROM latest_feats AS lf
        JOIN preferred_asof pa ON TRUE
        JOIN trading_universe AS tu
        ON tu.date = :trade_date
        AND tu.asof_time = pa.asof_time
        AND tu.symbol_id = lf.symbol_id;

        """)
    #TODO: create SQL query and upsert into strategy_signals table for k_value > 1
    # upsert_into_strategy_signals = text(""" INSERT INTO strategy_signals""")
    columns = ["ts","symbol_id", "symbol", "vwap_dev", "atr_pct"]
    with SessionLocal() as db:
        if focus_set.length() > 0:
            for stock, _ in focus_set:
                vwap_rows = db.execute(sql_query, {":symbol_id": focus_stocks, 
                                                   ":trade_date": current_date}).fetchall()
        else: 
            return ("Focus Set is empty")
        
    vwap_df = pd.DataFrame(vwap_rows,columns)
    vwap_df["vwap_dev"] = vwap_df["vwap_dev"].abs()
    vwap_df["atr_pct"] = vwap_df[vwap_df["atr_pct"] > 0]
    vwap_df["k_value"] = vwap_df["vwap_dev"]/vwap_df["atr_pct"]
    vwap_bounce_df = vwap_df[vwap_df["k_value"] > 1.0]

    return vwap_bounce_df










