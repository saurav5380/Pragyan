import os
from kiteconnect import KiteConnect
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta


api_key = os.environ.get("KITE_API_KEY")
access_key = os.environ.get("KITE_ACCESS_TOKEN")
kite = KiteConnect(api_key=api_key)
kite.set_access_token(access_token=access_key)

def avg_daily_volume(df, period=20):
    """
    Calculates the Average Daily Volume (ADV) for a DataFrame.

    Args:
        df (pd.DataFrame): DataFrame with a 'v' (volume) column.
        period (int): The number of periods for the rolling average.

    Returns:
        pd.DataFrame: The original DataFrame with an added ADV column.
    """
    df[f"ADV{period}"] = df['v'].rolling(window=period).mean()
    return df

def avg_true_range(df, period=14):
    """
    Calculates the Average True Range (ATR) for a DataFrame.

    Args:
        df (pd.DataFrame): DataFrame with 'h', 'l', and 'c' columns.
        period (int): The number of periods for the ATR calculation.

    Returns:
        pd.DataFrame: The original DataFrame with an added ATR column.
    """
    # Calculate the three True Range components
    tr1 = df['h'] - df['l']
    tr2 = abs(df['h'] - df['c'].shift(1)) # .shift(1) gets the previous day's close
    tr3 = abs(df['l'] - df['c'].shift(1))
    
    # Get the maximum of the three components to find the True Range (TR)
    true_range_df = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3})
    df['TR'] = true_range_df.max(axis=1)

    # Calculate the Simple Moving Average of the True Range to get ATR
    df[f"ATR{period}"] = df['TR'].rolling(window=period).mean()
    return df

def fetch_stock_quotes():    
    all_quotes = {}
    all_instruments = kite.instruments(exchange="NSE")
    try:
        all_stocks = [inst["tradingsymbol"] for inst in all_instruments if inst["instrument_type"] == "EQ"]
        batch_size = 500
        # kite.quote() expectes the equity to be passed in "EXCHANGE:SYMBOL" format
        prefix = "NSE:"
        equity = [prefix + item for item in all_stocks]
        for i in range(0,len(equity), batch_size):
            batch = equity[i : i+batch_size]
            quotes = kite.quote(batch)
            all_quotes.update(quotes)
            time.sleep(5)

    except Exception as e:
        print(f"Failed to retrieve data: {e}")
        return {}
    
    # filter out stocks which have hit Upper Circuit or Lower Circuit
    # Filter out symbols at circuit limits
    filtered_quotes = {}
    for symbol, q in all_quotes.items():
        ltp = q.get("last_price")
        lo  = q.get("lower_circuit_limit")
        hi  = q.get("upper_circuit_limit")
        if ltp is not None and lo is not None and hi is not None:
            if lo < ltp < hi:
                filtered_quotes[symbol] = q
    return filtered_quotes

def convert_quotes_to_dataframe(quotes_dict):
    quotes_list = []
    for symbol,quotes in quotes_dict.items():
        if 'ohlc' in quotes and 'volume' in quotes:
            ohlc = quotes.get('ohlc') or {}
            row = {
                'symbol': symbol,
                'instrument_token': quotes.get("instrument_token"),
                'o' : ohlc.get('open'),
                'h' : ohlc.get('high'),
                'l' : ohlc.get('low'),
                'c' : ohlc.get('close'),
                'v' : quotes.get('volume')
            }
            quotes_list.append(row)
    
    df = pd.DataFrame(quotes_list)
    
    return df

def get_historical_data(df):

    all_hist_frames = []
    to_date = datetime.now().date()
    from_date = to_date - timedelta(days=30)
    for _, row in df.iterrows():
        token = row.get("instrument_token")
        symbol = row.get("symbol")

        if not token or pd.isna(token):
            print(f"Skipping {row['symbol']} as instrument token is not available")
            continue
        
        try:
            hist_data = kite.historical_data(
                instrument_token=token, 
                from_date=from_date, 
                to_date=to_date,
                interval='day')
            if isinstance(hist_data,dict) and 'data' in hist_data and 'candles' in hist_data['data']:
                candles = hist_data['data']['candles']
            else:
                candles = hist_data
            temp_df = pd.DataFrame(candles, columns=["ts","o","h","l","c","v"])
            temp_df['symbol'] = row['symbol']
            temp_df["ts"] = pd.to_datetime(temp_df["ts"])
            for col in ["o","h","l","c"]:
                temp_df[col] = pd.to_numeric(temp_df[col], errors='coerce')
            temp_df['v'] = pd.to_numeric(temp_df['v'], errors='coerce').fillna(0).astype(dtype='int64')
            all_hist_frames.append(temp_df)
            time.sleep(2)
        
        except Exception as e:
            print(f"Error fetching {row['symbol']}: {e}")
            continue
    
    if not all_hist_frames:
        return pd.DataFrame(columns=["symbol","ts","o","h","l","c","v"])
    
    hist_df = pd.concat(all_hist_frames, ignore_index=True)
    hist_df.sort_values(['symbol','ts'], inplace=True)
    hist_df.drop_duplicates(["symbol", "ts"], keep='last', inplace=True)
    
    return hist_df

def create_universe():
    try:
        # fetch all stock quotes
        get_all_stock_quotes = fetch_stock_quotes()
        if not get_all_stock_quotes:
            print("No quotes returned. Empty Universe!")
            return pd.DataFrame()

        # convert quotes into a dataframe
        quotes_df = convert_quotes_to_dataframe(get_all_stock_quotes)
        
        # get historical data
        quotes_with_history_data = get_historical_data(quotes_df)
        if not quotes_with_history_data:
            print("No historical data.")
            return pd.DataFrame()

        # compute features on historical data
        hist_df = avg_daily_volume(quotes_with_history_data)
        hist_df = avg_true_range(hist_df)

        # merged df - to include 'instrument_token' 
        columns_for_merge = ["symbol","instrument_token"]
        merged_df = hist_df.merge(get_all_stock_quotes[columns_for_merge].drop_duplicates(), on='symbol', how='left')
        
        # filter the df based on ADV and ATR values
        filtered_df = merged_df[(merged_df["ADV20"] > 100000) & (merged_df["ATR14"] > 5)]

        
        
        

    except Exception as e:
        print(f"Failed to create trading universe: {e}")
        return []
    
    
    trading_universe = trading_universe.sort_values(["symbol","ts"], inplace=True).drop_duplicates()
    trading_universe = trading_universe.sort_values("ADV20", ascending=False).head(100)
    return trading_universe



















        


