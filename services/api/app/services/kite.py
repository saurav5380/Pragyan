# app/services/kite.py

# for production code
# import os
# from kiteconnect import KiteConnect

# def get_stocks():
#     api_key = os.environ.get("KITE_API_KEY")
#     access_token= os.environ.get("KITE_ACCESS_TOKEN") 
#     kite = KiteConnect(api_key=api_key)
#     kite.set_access_token(access_token)   

#     instruments = kite.instruments(exchange="NSE")

#     active_stocks = [
#         {
#              "exchange": inst["exchange"],
#             "ticker": inst["ticker"],
#             "name": inst["name"],
#             "sector": inst.get("sector") or "",
#             "tick_size": float(inst.get("tick_size", 0.05)),
#             "is_active": inst.get("active", True),
#         }
#         for inst in instruments
#         if inst.get("segment") == "NSE" and inst.get("instrument_type") == "EQ" and inst.get("exchange") == "NSE"
#     ]
#     return active_stocks


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
