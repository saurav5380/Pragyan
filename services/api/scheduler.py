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

scheduler = BackgroundScheduler()
kite = KiteConnect(api_key=kite_api_key)
kite.set_access_token(access_token=kite_access_token)

def fetch_price():
    try:
        stock_prices = []
        current_universe = create_universe() # get the current universe dataframe
        stocks = current_universe["symbol"]
        for stock in stocks:
            stock_prices.append(kite.quote(stock)) 
        column_mapping = {
            'volume': 'v',
            'high': 'h',
            'open': 'o',
            'close': 'c',
            'low': 'l'
        }
        temp_df = pd.DataFrame(stock_prices)
        current_stock_prices = temp_df.rename(columns=column_mapping)
    
    except Exception as e:
        print(f"Error: {e}")
    
    return current_stock_prices
  
scheduler.add_job(fetch_price,'interval',minutes=5)

print(f"Starting the scheduler")
scheduler.start()

try:    
    while True:
        time.sleep(2)
except (KeyboardInterrupt, SystemExit):
    print(f"Shutting down scheduler")
    scheduler.shutdown()



