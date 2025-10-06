# tests/test_features_misc.py
import pandas as pd
from services.api.app.services.features import macd

def test_macd_columns_exist_and_lengths_match():
    df = pd.DataFrame({"c": [i for i in range(1,200)]})
    out = macd(df.copy(), fast=12, slow=26, signal=9, price_col="c",
               out_macd="macd", out_sig="macd_sig")
    assert {"macd","macd_sig"}.issubset(out.columns)
    assert len(out["macd"]) == len(df)
    assert len(out["macd_sig"]) == len(df)
