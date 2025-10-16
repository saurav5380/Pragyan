# services/api/strategies/vwap_bounce.py

from redis import Redis
import os 
from sqlalchemy import text
from services.api.app.db import SessionLocal
import pandas as pd
import datetime
import pytz

#contants

ZSET_Key = "universe:latest"

r = Redis(
        host=os.environ.get("REDIS_HOST", "127.0.0.1"),
        port=int(os.environ.get("REDIS_PORT", 6379)),
        db=int(os.environ.get("REDIS_DB", 0)),
        password=os.environ.get("REDIS_PASSWORD"),
        decode_responses=True,  
    )


def vwap_bounce():
    focus_set = r.zrevrange(
        name=ZSET_Key,
        start=0,
        end=-1,
        withscores=True
    )

    # extract the names of stocks in the focus set 
    focus_stocks = [stock for stock, _ in focus_set]

    # NOTE: query now returns instrument_token as well (needed for NOT NULL insert)
    sql_query = text("""
        WITH preferred_asof AS (
            SELECT asof_time
            FROM trading_universe
            WHERE date = :trade_date
            GROUP BY asof_time
            ORDER BY
                CASE asof_time
                    WHEN '1230'    THEN 3
                    WHEN '0930'    THEN 2
                    WHEN 'preopen' THEN 1
                    ELSE 0
                END DESC
            LIMIT 1
        ),
        universe_today AS (
            SELECT
                tu.symbol_id,
                tu.instrument_token,
                tu.score,
                tu.rank,
                tu.adv20,
                tu.atr_pct AS daily_atr_pct
            FROM trading_universe tu
            JOIN preferred_asof pa
              ON tu.asof_time = pa.asof_time
            WHERE tu.date = :trade_date
              AND tu.instrument_token = ANY(:instrument_tokens)
        ),
        latest_feats AS (
            SELECT DISTINCT ON (f.symbol_id)
                f.symbol_id,
                f.ts,
                f.vwap,
                f.vwap_dev,
                f.atr_pct,
                f.rsi14,
                f.vol_z
            FROM features AS f
            JOIN universe_today ut
              ON f.symbol_id = ut.symbol_id
            WHERE f.atr_pct IS NOT NULL
              AND f.atr_pct > 0
              AND ((f.ts AT TIME ZONE 'Asia/Kolkata')::date = :trade_date)
            ORDER BY f.symbol_id, f.ts DESC
        )
        SELECT
            lf.symbol_id,
            lf.ts,
            lf.vwap,
            lf.vwap_dev,
            lf.atr_pct,
            lf.rsi14,
            lf.vol_z,
            ut.score       AS universe_score,
            ut.rank        AS universe_rank,
            ut.adv20,
            ut.daily_atr_pct,
            ut.instrument_token          -- << added
        FROM latest_feats lf
        JOIN universe_today ut
          ON ut.symbol_id = lf.symbol_id;
        """)

    # one-time safety: create a unique index to enable ON CONFLICT upsert
    create_unique_idx = text("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_strategy_signals_symbol_ts_strategy
        ON strategy_signals (symbol_id, ts, strategy_name);
    """)

    # UPSERT statement for strategy_signals with only NOT NULL columns
    upsert_signal_sql = text("""
        INSERT INTO strategy_signals (
            date,
            ts,
            symbol_id,
            instrument_token,
            strategy_name,
            side,
            signal_strength
        )
        VALUES (
            :date,
            :ts,
            :symbol_id,
            :instrument_token,
            :strategy_name,
            :side,
            :signal_strength
        )
        ON CONFLICT (symbol_id, ts, strategy_name)
        DO UPDATE SET
            side = EXCLUDED.side,
            signal_strength = EXCLUDED.signal_strength;
    """)

    with SessionLocal() as db:
        IST = pytz.timezone("Asia/Kolkata")
        current_time_ist = datetime.datetime.now(IST)
        current_date = current_time_ist.date()

        if len(focus_stocks) > 0:
            vwap_rows = db.execute(
                sql_query,
                {"instrument_tokens": focus_stocks, "trade_date": current_date}
            ).fetchall()
        else: 
            return ("Focus Set is empty")

        # Build DF in EXACT same order as SELECT (now includes instrument_token)
        columns = [
            "symbol_id","ts","vwap","vwap_dev","atr_pct","rsi14","vol_z",
            "universe_score","universe_rank","adv20","daily_atr_pct","instrument_token"
        ]
        vwap_df = pd.DataFrame(vwap_rows, columns)

        # VWAP-bounce calc
        vwap_df["vwap_dev"] = vwap_df["vwap_dev"].abs()
        vwap_df = vwap_df[vwap_df["atr_pct"] > 0]
        # if vwap_dev is absolute gap, convert to % by multiplying by 100 and dividing by atr_pct (already %)
        vwap_df["k_value"] = (vwap_df["vwap_dev"] * 100) / vwap_df["atr_pct"]
        vwap_bounce_df = vwap_df[vwap_df["k_value"] > 1.0]

        # If nothing qualifies, return the DF (no inserts)
        if vwap_bounce_df.empty:
            return vwap_bounce_df

        # Derive required fields for NOT NULL columns
        # side: mean-reversion interpretation (above VWAP → short; below → long)
        sides = vwap_bounce_df["vwap_dev"].copy()
        sides.loc[sides > 0] = "short"
        sides.loc[sides <= 0] = "long"

        # Prepare params for bulk upsert
        params = []
        for _, row in vwap_bounce_df.iterrows():
            params.append({
                "date": current_date,                              # IST trading date
                "ts": row["ts"],                                   # tz-aware bar close
                "symbol_id": int(row["symbol_id"]),
                "instrument_token": int(row["instrument_token"]),
                "strategy_name": "VWAP_Bounce_v1",
                "side": "short" if row["vwap_dev"] > 0 else "long",
                "signal_strength": float(row["k_value"])
            })

        # Ensure unique index exists, then upsert
        db.execute(create_unique_idx)
        if params:
            db.execute(upsert_signal_sql, params)
            db.commit()

    return vwap_bounce_df
