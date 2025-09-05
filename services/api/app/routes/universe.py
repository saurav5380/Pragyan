import os
from kiteconnect import KiteConnect
import pandas as pd
import pandas_ta as ta


api_key = os.environ.get("KITE_API_KEY")
access_key = os.environ.get("KITE_ACCESS_TOKEN")

def get_all_stocks():
    instruments = KiteConnect.instruments(exchange="NSE")
    equities = [
        {
            "exchange": inst["exchange"],
            "ticker": inst["tradingsymbol"],
            "name": inst["name"],
            "sector": inst.get("sector") or "",
            "tick_size": float(inst.get("tick_size", 0.05)),
            "instrument_token": inst.get("instrument_token", True),
            "last_price": inst.get("last_price", 0.0)
        }
        for inst in instruments
        if inst.get("segment") == "NSE" and inst.get("instrument_type") == "EQ"
    ]
    return equities



