from datetime import datetime
import pandas as pd
import time, os
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from kiteconnect import KiteConnect
from services.api.app.services.universe import create_universe
load_dotenv()
kite_api_key = os.getenv("KITE_API_KEY")
kite_access_token = os.getenv("KITE_ACCESS_TOKEN")

scheduler = BackgroundScheduler(timezone="Asia/Kolkata")
kite = KiteConnect(api_key=kite_api_key)
kite.set_access_token(access_token=kite_access_token)
current_universe = create_universe() # get the current universe dataframe
result = pd.DataFrame()



def fetch_price():
    # Guard against a empty universe 
    if current_universe is None or current_universe.empty or "symbol" not in current_universe:
        print("Universe is empty...skipping run")
        return result
    try:
        processed_list = []
        stocks = current_universe["symbol"].astype(str).to_list()
        stock_dict = kite.quote(stocks)
        column_mapping = {
            'ohlc_open': 'o',
            'ohlc_high': 'h',
            'ohlc_low': 'l',
            'ohlc_close': 'c',
            'volume': 'v'
        }
        
        for symbol, data in stock_dict.items():
            row = {"symbol": symbol}
            row["last_price"] = data.get("last_price")
            row["instrument_token"] = data.get("instrument_token")
            row["volume"] = data.get("volume")
            ohlc = data["ohlc"] or {}
            row['ohlc_open'] = ohlc.get('open')
            row['ohlc_high'] = ohlc.get('high')
            row['ohlc_low'] = ohlc.get('low')
            row['ohlc_close'] = ohlc.get('close')

            processed_list.append(row)

        if not processed_list:
            return result
        
        temp_df = pd.json_normalize(processed_list, sep='_')
        current_stock_prices = temp_df.rename(columns=column_mapping).copy()

        # adding a current timestamp to indicate the time the latest data fetch
        current_stock_prices["data_fetch_timestamp"] = datetime.now()
    
    except Exception as e:
        print(f"Error: {e}")
        return pd.DataFrame()
    
    return current_stock_prices
  
scheduler.add_job(fetch_price,
                  'interval',
                  minutes=5, 
                  coalesce=True, 
                  max_instances=1)

print(f"Starting the scheduler")
scheduler.start()

try:    
    while True:
        time.sleep(2)
except (KeyboardInterrupt, SystemExit):
    print(f"Shutting down scheduler")
    scheduler.shutdown()



