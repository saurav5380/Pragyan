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
        equity = [inst["tradingsymbol"] for inst in all_instruments if inst["instrument_type"] == "EQ"]
        batch_size = 500

        for i in range(0,len(equity), batch_size):
            batch = equity[i : i+batch_size]
            quotes = kite.quote(batch)
            all_quotes.update(quotes)
            time.sleep(5)

    except Exception as e:
        print(f"Failed to retrieve data: {e}")
        return {}
    
    # filter out stocks which have hit Upper Circuit or Lower Circuit
    filtered_quotes = {}
    for symbol, quotes in all_quotes.items():
        if "last_price" in quotes and "lower_circuit_limit" in quotes and "upper_circuit_limit" in quotes:
            if quotes["last_price"] > quotes["lower_circuit_limit"] and quotes["last_price"] < quotes["upper_circuit_limit"]:
                filtered_quotes[symbol] = quotes

    return filtered_quotes

def convert_quotes_to_dataframe(quotes_dict):
    quotes_list = []
    for symbol,quotes in quotes_dict.items():
        if 'ohlc' in quotes and 'volume' in quotes:
            ohlc = quotes['ohlc']
            row = {
                'symbol': symbol,
                'instrument_token': quotes["instrument_token"],
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

    all_hist = []
    to_date = datetime.now().date()
    from_date = to_date - timedelta(days=30)
    for idx, row in df.iterrows():
        instrument_token = row["instrument_token"]
        if instrument_token is None:
            print(f"Skipping {row['symbol']} as instrument token is not available")
            continue
        
        try:
            hist_data = kite.historical_data(instrument_token=instrument_token, from_date=from_date, to_date=to_date,interval='day')
            temp_df = pd.DataFrame(hist_data)
            temp_df['symbol'] = row['symbol']
            all_hist.append(temp_df)
        except Exception as e:
            print(f"Error fetching {row['symbol']}: {e}")
    
    if all_hist:
        hist_df = pd.concat(all_hist, ignore_index=True)
    
    quotes_with_historical_data = hist_df.merge(df, on='symbol', how='left')

    return quotes_with_historical_data 

def create_universe():
    try:
        # fetch all stock quotes
        get_all_stock_quotes = fetch_stock_quotes()

        # convert quotes into a dataframe
        quotes_dataframe = convert_quotes_to_dataframe(get_all_stock_quotes)
        
        # get historical data
        quotes_with_history_data = get_historical_data(quotes_dataframe)

        # Apply ADV and ATR filters 
        quotes_with_ADV = avg_daily_volume(quotes_with_history_data)
        quotes_with_ATR = avg_true_range(quotes_with_ADV)
    
    except Exception as e:
        print(f"Failed to create trading universe: {e}")
        return []

    trading_universe = quotes_with_ATR[(quotes_with_ATR["ADV20"] > 100000) & (quotes_with_ATR["ATR14"] > 5)]
    trading_universe = trading_universe.sort_values("ADV20", ascending=False).head(100)
    return trading_universe



















        


