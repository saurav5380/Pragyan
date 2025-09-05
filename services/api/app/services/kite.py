# app/services/kite.py

# for production code
# import os
# from datetime import date
# from kiteconnect import KiteConnect

# api_key = os.environ.get("KITE_API_KEY")
# access_token= os.environ.get("KITE_ACCESS_TOKEN") 
# kite = KiteConnect(api_key=api_key)
# kite.set_access_token(access_token)   

# def get_stocks():
#     instruments = kite.instruments(exchange="NSE")
#     active_stocks = [
#         {
#             "exchange": inst["exchange"],
#             "ticker": inst["tradingsymbol"],
#             "name": inst["name"],
#             "sector": inst.get("sector") or "",
#             "tick_size": float(inst.get("tick_size", 0.05)),
#             "is_active": inst.get("active", True),
#         }
#         for inst in instruments
#         if inst.get("segment") == "NSE" and inst.get("instrument_type") == "EQ" 
#     ]
#     return active_stocks

# def get_historical_data(symbol, from_date, to_date, interval="5m"):
#     historical_data = kite.historical_data(instrument_token=symbol, from_date=from_date, to_date=to_date, interval=interval)
#     return historical_data

def get_stocks():
    """
    Dummy function for now. In production, fetches from Kite Connect API.
    Returns:
        List[Dict]: Each dict has symbol details.
    """
    # Example: return 5 NSE stocks as dummy data
    return [
        {
            "exchange": "NSE",
            "ticker": "RELIANCE",
            "name": "RELIANCE INDUSTRIES",
            "sector": "REFINERIES",
            "tick_size": 0.05,
            "is_active": True,
        },
        {
            "exchange": "NSE",
            "ticker": "TCS",
            "name": "TATA CONSULTANCY SERVICES",
            "sector": "IT SERVICES",
            "tick_size": 0.05,
            "is_active": True,
        },
        {
            "exchange": "NSE",
            "ticker": "INFY",
            "name": "INFOSYS LTD",
            "sector": "IT SERVICES",
            "tick_size": 0.05,
            "is_active": True,
        },
        {
            "exchange": "NSE",
            "ticker": "HDFCBANK",
            "name": "HDFC BANK LTD",
            "sector": "BANKING",
            "tick_size": 0.05,
            "is_active": True,
        },
        {
            "exchange": "NSE",
            "ticker": "ICICIBANK",
            "name": "ICICI BANK LTD",
            "sector": "BANKING",
            "tick_size": 0.05,
            "is_active": True,
        },
    ]

def get_historical_data(symbol, from_date, to_date, interval="5m"):
    """
    Fetch historical OHLCV candles for a symbol from Kite API.
    Returns: List of dicts with time, open, high, low, close, volume, etc.
    """
    # Kite API to be called here 
    return [
        {
            "symbol": "RELIANCE",
            "date": from_date,   # datetime or string
            "open": 100.0,
            "high": 102.0,
            "low":  99.5,
            "close": 101.0,
            "volume": 150000,
            "timeframe": interval,
        },
        {
            "symbol": "TCS",
            "date": from_date,   # datetime or string
            "open": 1000.0,
            "high": 1020.0,
            "low":  990,
            "close": 1010.0,
            "volume": 3000,
            "timeframe": interval,
        },
    ]