import os
from kiteconnect import KiteConnect
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import time


api_key = os.environ.get("KITE_API_KEY")
access_key = os.environ.get("KITE_ACCESS_TOKEN")

def get_all_stocks():
    kite = KiteConnect(api_key=api_key)
    instruments = kite.instruments(exchange="NSE")
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

def avg_daily_volume(df, period=20):
    df[f"ADV{period}"] = ta.sma(df['v'], length=period)
    return df

def avg_true_range(df, period=14):
    df[f"ATR{period}"] = ta.atr(df['h'], df['l'], df['c'], length=period)
    return df

def fetch_all_stocks():
    kite = KiteConnect(api_key=api_key)
    all_quotes = {}
    try:
        equity = get_all_stocks()
        batch_size = 500

        for i in range(0,len(equity), batch_size):
            batch = equity[i : i+batch_size]
            quotes = kite.quote(batch)
            all_quotes.update(quotes)

    except Exception as e:
        print(f"Falied to retrieve data: {e}")
    
    time.sleep(5)

    return all_quotes


        


