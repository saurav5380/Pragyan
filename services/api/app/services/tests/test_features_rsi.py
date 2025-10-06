import pandas as pd
import numpy as np
from services.api.app.services.features import rsi

def test_rsi():
    prices = pd.Series([100,101,102,103,102,101,100,99,98,99,100,101,102,103,104,105])
    df = pd.DataFrame({"c": prices})
    out = rsi(df, period=14, price_col='c', out_col="rsi14")

    #Assert
    assert "rsi14" in out.columns

    # drop na values
    valid = out["rsi14"].dropna()
    assert (valid >= 0).all() and (valid <=100).all()

