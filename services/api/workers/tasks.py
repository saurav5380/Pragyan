import pandas as pd
from datetime import datetime, timedelta
from app.services.kite import get_historical_data
from app.celery_app import celery_app
from app.db import SessionLocal
from app.services.features import compute_features

'''The below are Celery tasks which are written in a 'fan-out' pattern
In the 'fan-out' pattern --> One Parent task which is the function 'update_all_stocks_5m()' is called 
The parent task now calls upon other 'child' tasks like 'update_price_task()' and 'ingest_candles()'
'''


def ingest_candles(symbol, interval="5m", days=60): 
    to_date = datetime.now() 
    from_date = to_date - timedelta(days=days)
    candle_data = get_historical_data(instrument_token=symbol, from_date=from_date, to_date=to_date, interval=interval) 
    # <---- Code to store candle_data in DB ----->
    return candle_data

@celery_app.task
def update_price_task(symbol, interval="5m"):
    days=1
    candles = ingest_candles(symbol,interval,days)
    print("Candle Data ingested for ${symbol}")
    return len(candles)

@celery_app.task 
def update_all_stocks_5m(): 
    db = SessionLocal()
    symbols = db.execute("SELECT ticker FROM symbols WHERE is_active = true").fetchall()
    db.close()

    for symbol_row in symbols:
        symbol = symbol_row[0]
        update_price_task.delay(symbol,"5m")
    
    return f"Queued price update for {len(symbols)}"

@celery_app.task
def calc_features():
    try:
        db = SessionLocal()
        count = 0
        symbol_id = [row[0] for row in db.execute("SELECT id FROM symbols where is_active = true").fetchall()]
        for id in symbol_id:
            rows = db.execute("SELECT symbol_id, ts, o, h, c, l, v from candles WHERE symbol_id = :symbol_id", {"symbol_id": symbol_id}).fetchall()
            if not rows:
                continue
            df = pd.DataFrame(rows, columns=["symbol_id", "ts", "o", "h", "c", "l", "v"])
            features_df = compute_features(df)
            for _, row in features_df:
                db.execute("INSERT INTO features (symbol_id, ts, rsi14, macd, macd_sig, atr14, vwap, vwap_dev, vol_z, ma50, ma200) "
                           "VALUES (:symbol_id, :ts, :rsi14, :macd, :macd_sig, :atr14, :vwap, :vwap_dev, :vol_z, :ma50, :ma200) "
                           "ON CONFLICT (symbol_id, ts) DO UPDATE SET "
                           "rsi14 = EXCLUDED.rsi14, macd = EXCLUDED.macd, macd_sig = EXCLUDED.macd_sig, atr14 = EXCLUDED.atr14,"
                           "vwap = EXCLUDED.vwap, vwap_dev = EXCLUDED.vwap_dev, vol_z = EXCLUDED.vol_z, ma50 = EXCLUDED.ma50, ma200 = EXCLUDED.ma200 ",
                           {
                            "symbol_id" : row["symbol_id"],
                            "ts": row["ts"],
                            "rsi14": row.get("rsi14"),
                            "macd": row.get("macd"),
                            "macd_sig": row.get("macd_sig"),
                            "atr14": row.get("atr14"),
                            "vwap": row.get("vwap"),
                            "vwap_dev": row.get("vwap_dev"),
                            "vol_z": row.get("vol_z"),
                            "ma50": row.get("ma50"),
                            "ma200": row.get("ma200"),
                           }
                           )
                db.commit()
                count += 1
                return f"Features created for {count} stocks"
    finally:
        db.close()
        
    
    






