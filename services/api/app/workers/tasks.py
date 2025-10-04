
'''The below are Celery tasks which are written in a 'fan-out' pattern
In the 'fan-out' pattern --> One Parent task which is the function 'update_all_stocks_5m()' is called 
The parent task now calls upon other 'child' tasks like 'update_price_task()' and 'ingest_candles()'
''' 

import pandas as pd
from datetime import datetime, timedelta, timezone
from app.services.kite import get_historical_data
from sqlalchemy import text
from app.celery_app import celery_app
from app.db import SessionLocal
from app.services.features import (compute_features, FeatureConfig, required_warmup_bars)
from celery import chain
from celery.signals import task_success, task_failure


"""
Function ingest_candles fetches the historical_data of the past 60 days 
and writes into the SQL table -> candles
"""
def ingest_candles(symbol_id: int, instrument_token: str, interval:str = "5m", days:int = 60) -> pd.DataFrame: 
    to_date = datetime.now(timezone.utc) 
    from_date = to_date - timedelta(days=days)
    candle_data = get_historical_data(instrument_token=instrument_token, from_date=from_date, to_date=to_date, interval=interval) 
    # <---- Code to store candle_data in DB ----->
    candle_df = pd.DataFrame(candle_data)
    if candle_df.empty:
        return candle_df
    df = candle_df.rename(columns={"date": "ts", "open": "o", "high": "h", "low": "l", "close": "c", "volume": "v"})
    df = df[["ts","o","h","c","l","v"]].sort_values("ts").reset_index(drop=True)

    #Upsert to DB
    with SessionLocal() as db:
        params = [
            {
                "symbol_id": symbol_id,
                "ts": row.ts,
                "o": float(row.o),
                "h": float(row.h),
                "l": float(row.l),
                "c": float(row.c),
                "v": float(row.v),
                "timeframe": interval,
            }
            for row in df.itertuples(index=False)
        ]
        db.execute(text(""" 
            INSERT INTO candles (symbol_id, ts, o, h, l, c, v, timeframe)
            VALUES (:symbol_id, :ts, :o, :h, :l, :c, :v, :timeframe)
            ON CONFLICT (symbol_id, ts, timeframe) DO UPDATE SET
              o = EXCLUDED.o, h = EXCLUDED.h, l = EXCLUDED.l,
              c = EXCLUDED.c, v = EXCLUDED.v
        """), params)
        db.commit()
    return df

@celery_app.task(autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def update_price_task(symbol_id: int, instrument_token: str, interval: str ="5m") -> int:
    days=1
    candles = ingest_candles(symbol_id, instrument_token, interval, days)
    print(f"Candle Data ingested for {instrument_token}")
    return len(candles)

# update price of all stocks in the trading universe 
@celery_app.task 
def update_all_stocks_5m() -> str: 
    db = SessionLocal()
    symbols = db.execute("SELECT symbol_id, instrument_token FROM trading_universe").fetchall()
    db.close()

    for symbol_id, token in symbols:
        update_price_task.delay(symbol_id,token,"5m")
    
    return f"Queued price update for {len(symbols)}"

@celery_app.task(autoretry_for=(Exception,),retry_backoff=True, max_retries=3)
def calc_features(interval: str = "5m") -> str:
    cfg = FeatureConfig()
    warmup = required_warmup_bars(cfg, interval)
    with SessionLocal() as db:
        symbols = db.execute(text("SELECT symbol_id, instrument_token FROM trading_universe ")).fetchall()

        total_written = 0
        for symbol_id, instrument_token in symbols:
            # Load a compute window with warmup; here: last 2 trading days + warmup safety
            to_dt = datetime.now(timezone.utc)
            from_dt = to_dt - timedelta(days=3)

            # Pull from DB (prefer DB so we don’t double-call provider here)
            rows = db.execute(text("""
                SELECT ts, o, h, l, c, v
                FROM candles
                WHERE symbol_id = :sid
                  AND timeframe = :tf
                  AND ts BETWEEN :from_dt AND :to_dt
                ORDER BY ts ASC
            """), {"sid": symbol_id, "tf": interval, "from_dt": from_dt, "to_dt": to_dt}).fetchall()

            # if not rows:
            #     # Fallback: try fetch from provider (optional)
            #     ingest_candles(symbol_id, instrument_token, interval, days=3)
            #     rows = db.execute(text("""
            #         SELECT ts, o, h, l, c, v
            #         FROM candles
            #         WHERE symbol_id = :sid AND timeframe = :tf
            #         AND ts BETWEEN :from_dt AND :to_dt
            #         ORDER BY ts ASC
            #     """), {"sid": symbol_id, "tf": interval, "from_dt": from_dt, "to_dt": to_dt}).fetchall()

            if not rows:
                print("No rows of data returned from candles table")
                continue

            df = pd.DataFrame(rows, columns=["ts","o","h","l","c","v"]).sort_values("ts").reset_index(drop=True)

            # Keep enough warmup rows at the head for stable indicators
            df = df.iloc[-(warmup + 600) :]  # 600 compute bars ~ adjust for your cadence

            # Compute features (mutates df)
            df = compute_features(df, cfg)

            # Prepare batch upsert rows (drop early NaNs if desired)
            payload = []
            for row in df.itertuples(index=False):
                payload.append({
                    "symbol_id": symbol_id,
                    "ts": row.ts,
                    "rsi14": getattr(row, "rsi14", None),
                    "macd": getattr(row, "macd", None),
                    "macd_sig": getattr(row, "macd_sig", None),
                    "atr14": getattr(row, "atr14", None),
                    "atr_pct": getattr(row, "atr_pct", None),
                    "vwap": getattr(row, "vwap", None),
                    "vwap_dev": getattr(row, "vwap_dev", None),
                    "vol_z": getattr(row, "vol_z", None),
                    "ma50": getattr(row, "ma50", None),
                    "ma200": getattr(row, "ma200", None),
                    "adtv": getattr(row, "adtv", None),
                })

            if not payload:
                continue

            db.execute(text("""
                INSERT INTO features (
                    symbol_id, ts, rsi14, macd, macd_sig, atr14, atr_pct,
                    vwap, vwap_dev, vol_z, ma50, ma200, adtv
                )
                VALUES (
                    :symbol_id, :ts, :rsi14, :macd, :macd_sig, :atr14, :atr_pct,
                    :vwap, :vwap_dev, :vol_z, :ma50, :ma200, :adtv
                )
                ON CONFLICT (symbol_id, ts) DO UPDATE SET
                    rsi14 = EXCLUDED.rsi14,
                    macd = EXCLUDED.macd,
                    macd_sig = EXCLUDED.macd_sig,
                    atr14 = EXCLUDED.atr14,
                    atr_pct = EXCLUDED.atr_pct,
                    vwap = EXCLUDED.vwap,
                    vwap_dev = EXCLUDED.vwap_dev,
                    vol_z = EXCLUDED.vol_z,
                    ma50 = EXCLUDED.ma50,
                    ma200 = EXCLUDED.ma200,
                    adtv = EXCLUDED.adtv
            """), payload)
            db.commit()
            total_written += len(payload)
    return f"Features upserted rows: {total_written}"
    
    
@celery_app.task(bind=True)
def run_trade_pipeline(self):
    pipeline = chain(
        update_all_stocks_5m.s(),
        calc_features.s()
    )

    result = pipeline()
    return result

@task_success.connect
def on_success(sender, result, **kwargs):
    print(f"Task {sender.name} succeded. Result: {result}")

@task_failure.connect
def on_failure(sender, exc, task_id, args, kwargs, einfo, **_):
    print(f"Task {sender.name} failed. Task-id: {task_id}")
    print(f"\n Task Exception: {exc}")
    print(f"\n Traceback: {einfo}")








