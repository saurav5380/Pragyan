from datetime import datetime, timedelta
from app.services.kite import get_historical_data
from app.celery_app import celery_app

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



