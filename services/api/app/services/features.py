import pandas as pd
import numpy as np
# monkey patch
if not hasattr(np, "NaN"):
    np.NaN = np.nan

import pandas_ta as ta

def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    #RSI
    df["rsi14"] = ta.rsi(df["c"], length=14)
    
    #MACD
    macd = ta.macd(df["c"])
    df["macd"] = macd["MACD_12_26_9"]
    df["macd_sig"] = macd["MACDs_12_26_9"]

    #ATR
    df["atr14"] = ta.atr(df["h"], df["l"], df["c"],period=14)

    #VWAP
    df["vwap"] = ta.vwap(df["h"], df["l"], df["c"], df["v"])

    #VWAP Deviation
    df["vwap_dev"] = (df["c"] - df["vwap"])/df["vwap"]

    #Z-Score
    df["vol_z"] = (df["v"] - df["v"].rolling(20).mean())/ df["v"].rolling(20).std()

    #MA 50
    df["ma50"] = ta.sma(df["c"], length=50)
    
    #MA200
    df["ma200"] = ta.sma(df["c"], length=200)

    return df







