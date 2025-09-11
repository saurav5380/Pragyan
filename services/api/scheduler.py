from datetime import datetime
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
    # get the current universe dataframe
    current_universe = create_universe()
    




    
scheduler.add_job(fetch_price,'interval',minutes=5)

print(f"Starting the scheduler")
scheduler.start()

try:    
    while True:
        time.sleep(2)
except (KeyboardInterrupt, SystemExit):
    print(f"Shutting down scheduler")
    scheduler.shutdown()



