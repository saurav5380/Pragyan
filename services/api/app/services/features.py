import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional, Iterable, Literal

# -----------------------
#         Config
# -----------------------
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

# -----------------------
#     Helper Functions
# -----------------------

def _ema(s: pd.Series, span: int) -> pd.Series:
    return s.ewm(span=span, adjust=False, min_periods=span)

def _rolling_zscore(s: pd.Series, window: int) -> pd.Series:
    m = s.rolling(window, min_periods=max(5, window // 3)).mean()
    sd = s.rolling(window, min_periods=max(5, window // 3)).std(ddof=0)
    return (s-m)/sd

def _true_range(h: pd.Series, l: pd.Series, c_prev: pd.Series) -> pd.Series:
    a = h - l
    b = (h - c_prev).abs()
    c = (l - c_prev).abs()
    return pd.concat([a,b,c],axis=1).max(axis=1)

def _session_id_from_ts(ts: pd.Series) -> pd.Series:
    return ts.dt.date

def _ensure_cols(df: pd.Dataframe, cols: Iterable[str]) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required Columns : {missing}")


# -----------------------
#     Indicators
# -----------------------

def rsi(df: pd.DataFrame, period: int = 14, price_col: str = "c", out_col: str = "rsi14") -> pd.DataFrame:
    _ensure_cols(df, [price_col])
    delta = df[price_col].diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df[out_col] = 100 - (100 / (1 + rs))
    return df

def macd(df: pd.DataFrame,
         fast: int = 12, slow: int = 26, signal: int = 9,
         price_col: str = "c",
         out_macd: str = "macd", out_sig: str = "macd_sig") -> pd.DataFrame:
    _ensure_cols(df, [price_col])
    ema_fast = _ema(df[price_col], fast)
    ema_slow = _ema(df[price_col], slow)
    macd_line = ema_fast - ema_slow
    sig_line = _ema(macd_line, signal)
    df[out_macd] = macd_line
    df[out_sig] = sig_line
    return df

def atr(df: pd.DataFrame, period: int = 14,
        out_col: str = "atr14", out_pct_col: Optional[str] = "atr_pct") -> pd.DataFrame:
    _ensure_cols(df, ["h", "l", "c"])
    tr = _true_range(df["h"], df["l"], df["c"].shift(1))
    df[out_col] = tr.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    if out_pct_col:
        df[out_pct_col] = (df[out_col] / df["c"]) * 100.0
    return df

def moving_averages(df: pd.DataFrame, short: int = 50, long: int = 200,
                    price_col: str = "c",
                    out_short: str = "ma50", out_long: str = "ma200") -> pd.DataFrame:
    _ensure_cols(df, [price_col])
    df[out_short] = df[price_col].rolling(short, min_periods=short//2).mean()
    df[out_long] = df[price_col].rolling(long, min_periods=long//2).mean()
    return df

def vwap(df: pd.DataFrame,
         sessionize: bool = True,
         out_price: str = "vwap",
         out_dev: str = "vwap_dev") -> pd.DataFrame:
    _ensure_cols(df, ["ts", "h", "l", "c", "v"])
    typical = (df["h"] + df["l"] + df["c"]) / 3.0
    if sessionize:
        sid = _session_id_from_ts(df["ts"])
        # cumulative per session
        tpv = (typical * df["v"]).groupby(sid).cumsum()
        vol = df["v"].groupby(sid).cumsum()
        vw = tpv / vol.replace(0, np.nan)
    else:
        tpv = (typical * df["v"]).cumsum()
        vol = df["v"].cumsum()
        vw = tpv / vol.replace(0, np.nan)
    df[out_price] = vw
    df[out_dev] = (df["c"] - df[out_price]) / df[out_price]  # relative deviation, e.g. 0.012 = +1.2%
    return df

def volume_zscore(df: pd.DataFrame, window: int = 20, out_col: str = "vol_z") -> pd.DataFrame:
    _ensure_cols(df, ["v"])
    df[out_col] = _rolling_zscore(df["v"], window)
    return df

def relative_strength(df: pd.DataFrame,
                      baseline_close: Optional[pd.Series],
                      price_col: str = "c",
                      out_col: str = "rel_strength") -> pd.DataFrame:
    """
    Very simple RS proxy: ratio vs baseline (e.g., NIFTY500 close), normalized by a rolling mean.
    Assumes baseline_close is aligned by index with df.
    """
    if baseline_close is None:
        df[out_col] = np.nan
        return df
    _ensure_cols(df, [price_col])
    ratio = df[price_col] / baseline_close
    rs = ratio / ratio.rolling(20, min_periods=10).mean()
    df[out_col] = rs
    return df

def adtv(df: pd.DataFrame,
         window_days: int = 20,
         out_col: str = "adtv",
         scale_to_crore: bool = True) -> pd.DataFrame:
    """
    Average Daily Traded Value over N days.
    If intraday, we first aggregate to daily (sum of v*c) then roll.
    Returns a column aligned at the bar level (forward-filled per day).
    """
    _ensure_cols(df, ["ts", "c", "v"])
    # Aggregate to daily traded value
    day = df["ts"].dt.date
    dtv_daily = (df["c"] * df["v"]).groupby(day).sum().astype(float)
    adtv_daily = dtv_daily.rolling(window_days, min_periods=max(5, window_days//3)).mean()
    if scale_to_crore:
        adtv_daily = adtv_daily / 1e7  # ₹ -> ₹ Crore (1 Cr = 1e7)
    # Map back to rows
    df[out_col] = adtv_daily.reindex(day).values
    return df

# -----------------------
#     Orchestrator
# -----------------------
def compute_features(df: pd.DataFrame, 
                     cfg: FeatureConfig = FeatureConfig(), 
                     include: Optional[Iterable[str]] = None
                    ):
    _ensure_cols(df,["ts","o","h","l","c","v"])
    df = df.sort_values("ts").reset_index(drop=True).copy()
    todo = set(include) if include else {"rsi", "macd", "atr", "vwap", "vol_z", "ma", "adtv"}

    if "rsi" in todo:
        rsi(df,period=cfg.rsi_period)
    
    if "macd" in todo:
        macd(df, fast=cfg.macd_fast, slow=cfg.macd_slow, signal=cfg.macd_signal)

    if "atr" in todo:
        atr(df, period=cfg.atr_period, out_col="atr14", out_pct_col="atr_pct")
    
    if "vwap" in todo:
        vwap(df, sessionize=cfg.vwap_sessionize, out_price="vwap", out_dev="vwap_dev")
    
    if "vol_z" in todo:
        volume_zscore(df, window=cfg.vol_z_window, out_col="vol_z")
    
    if "ma" in todo:
        moving_averages(df, short=cfg.ma_short, long=cfg.ma_long, out_short="ma50", out_long="ma200")
    
    if "adtv" in todo:
        adtv(df, window_days=cfg.adtv_window_days, out_col="adtv", scale_to_crore=cfg.currency_scale_to_crore)

    
    # creating relative strength of index to calculate RSI
    if cfg.baseline_rs is not None and "rs" in todo:
        relative_strength(df,baseline_close=cfg.baseline_rs, out_col="rel_strength")
    

# -----------------------
#     Warm Up candles
# -----------------------
    
def required_warmup_bars(cfg:FeatureConfig = FeatureConfig(), 
                         timeframe: Literal["1m","3m","5m","15m","1d"] = "5m") -> int: 
    key = [
        cfg.rsi_period,
        cfg.macd_slow + cfg.macd_signal,
        cfg.atr_period,
        cfg.ma_long,
        cfg.vol_z_window
    ]
    base = int(max(key) * 1.5)
    # For sessionized VWAP, add a session to be safe on open
    if timeframe != "1d":
        base += 50  # ~ first hour buffer
    return base



    

    








