from datetime import datetime, timedelta
from app.services.kite import get_historical_data
from app.celery_app import celery_app
from app.db import SessionLocal

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




