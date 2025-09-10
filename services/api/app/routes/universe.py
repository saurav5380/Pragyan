import os
from kiteconnect import KiteConnect
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import time


api_key = os.environ.get("KITE_API_KEY")
access_key = os.environ.get("KITE_ACCESS_TOKEN")

def avg_daily_volume(df, period=20):
    df[f"ADV{period}"] = ta.sma(df['v'], length=period)
    return df

def avg_true_range(df, period=14):
    df[f"ATR{period}"] = ta.atr(df['h'], df['l'], df['c'], length=period)
    return df

def fetch_stock_quotes():
    kite = KiteConnect(api_key=api_key)
    all_quotes = {}
    all_instruments = kite.instruments(exchange="NSE")
    try:
        equity = [inst["tradingsymbol"] for inst in all_instruments if inst["instrument_type"] == "EQ"]
        batch_size = 500

        for i in range(0,len(equity), batch_size):
            batch = equity[i : i+batch_size]
            quotes = kite.quote(batch)
            all_quotes.update(quotes)

    except Exception as e:
        print(f"Falied to retrieve data: {e}")
    
    time.sleep(5)

    return all_quotes

get_all_stock_quotes = fetch_stock_quotes()





        


