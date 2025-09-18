import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional

@dataclass
class FeatureConfig:
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    atr_period: int = 14
    ma_short: int = 50
    ma_long: int = 200
    vol_z_window: int = 20
    adtv_window_days: int = 20
    baseline_rs: Optional[pd.Series] = None
    vwap_sessionize: bool = True
    currency_scale_to_crore: bool = True

    










