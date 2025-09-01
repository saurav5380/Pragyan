from datetime import datetime, timedelta
from app.services.kite import get_historical_data

def ingest_candles(symbol, interval="5m", days=60): 
    to_date = datetime.now() 
    from_date = to_date - timedelta(days=days)
    candle_data = get_historical_data(instrument_token=symbol, from_date=from_date, to_date=to_date, interval=interval) 
    # <---- Code to store candle_data in DB ----->
    return candle_data
