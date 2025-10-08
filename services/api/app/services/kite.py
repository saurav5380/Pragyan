import os
from kiteconnect import KiteConnect
from dotenv import load_dotenv

load_dotenv()

api_key = os.environ.get("KITE_API_KEY")
request_token = os.environ.get("KITE_REQUEST_TOKEN")
api_secret = os.environ.get("KITE_API_SECRET_KEY")

kite = KiteConnect(api_key=api_key)
token = kite.generate_session(request_token, api_secret)
access_token = token["access_token"]
kite.set_access_token(access_token)   
print(access_token)

def get_stocks():
    instruments = kite.instruments(exchange="NSE")
    active_stocks = [
        {
            "exchange": inst["exchange"],
            "ticker": inst["tradingsymbol"],
            "name": inst["name"],
            "sector": inst.get("sector") or "",
            "tick_size": float(inst.get("tick_size", 0.05)),
            "instrument_token": inst.get("instrument_token", 0),
            "last_price": inst.get("last_price", 0.0)
        }
        for inst in instruments
        if inst.get("segment") == "NSE" and inst.get("instrument_type") == "EQ" 
    ]
    return active_stocks

def get_historical_data(instrument_token, from_date, to_date, interval="5m"):
    historical_data = kite.historical_data(instrument_token=instrument_token, from_date=from_date, to_date=to_date, interval=interval)
    return historical_data
    
