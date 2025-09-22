# services/api/app/models.py
from __future__ import annotations

from typing import Optional, List
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    Date, String, Integer, BigInteger, DateTime, Numeric,
    ForeignKey, Index, UniqueConstraint, PrimaryKeyConstraint, Boolean, func
)

from db import Base  # Base lives in services/api/db.py 

# ---------------------------
# symbols
# ---------------------------
class Symbol(Base):
    __tablename__ = "symbols"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    exchange: Mapped[str] = mapped_column(String(8), nullable=False)
    ticker: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(64))
    sector: Mapped[Optional[str]] = mapped_column(String(128))
    tick_size: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    instrument_token: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    last_price: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    # Unique constraint (exchange, ticker)
    __table_args__ = (
        UniqueConstraint("exchange", "ticker", name="uq_symbols_exchange_ticker"),
    )

    # Relationships
    candles: Mapped[List["Candle"]] = relationship(
        back_populates="symbol", cascade="all, delete-orphan"
    )
    features: Mapped[List["Feature"]] = relationship(
        back_populates="symbol", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Symbol {self.exchange}:{self.ticker}>"

# ---------------------------
# candles   (Timescale hypertable is created in a migration)
# PK: (symbol_id, ts, timeframe)
# ---------------------------
class Candle(Base):
    __tablename__ = "candles"

    symbol_id: Mapped[int] = mapped_column(
        ForeignKey("symbols.id", ondelete="CASCADE"), nullable=False
    )
    ts: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)

    o: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    c: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    h: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    l: Mapped[float] = mapped_column(Numeric(14, 4), nullable=False)
    v: Mapped[int] = mapped_column(BigInteger, nullable=False)
    timeframe: Mapped[str] = mapped_column(String(8), nullable=False)

    symbol: Mapped["Symbol"] = relationship(back_populates="candles")

    __table_args__ = (
        PrimaryKeyConstraint("symbol_id", "ts", "timeframe", name="pk_candles"),
        Index("ix_candles_symbol_tf_ts", "symbol_id", "timeframe", "ts"),
    )

# ---------------------------
# features
# PK: (symbol_id, ts)
# ---------------------------
class Feature(Base):
    __tablename__ = "features"

    symbol_id: Mapped[int] = mapped_column(
        ForeignKey("symbols.id", ondelete="CASCADE"), nullable=False
    )
    ts: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)

    rsi14: Mapped[Optional[float]] = mapped_column(Numeric(6, 3))
    macd: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    macd_sig: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    atr14: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    atr_pct: Mapped[Optional[float]] = mapped_column(Numeric(10,4))
    vwap: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    vwap_dev: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    vol_z: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    adtv: Mapped[Optional[float]] = mapped_column(Numeric(10, 4))
    ma50: Mapped[Optional[float]] = mapped_column(Numeric(14, 4))
    ma200: Mapped[Optional[float]] = mapped_column(Numeric(14, 4))

    symbol: Mapped["Symbol"] = relationship(back_populates="features")

    __table_args__ = (
        PrimaryKeyConstraint("symbol_id", "ts", name="pk_features"),
        Index("ix_features_symbol_ts", "symbol_id", "ts"),
    )

# ---------------------------
# Universe  (Daily Trading Universe )
# PK: (symbol_id, ts, timeframe)
# ---------------------------
class Trading_Universe(Base):
    __tablename__ = "trading_universe"

    date: Mapped[Date] = mapped_column(Date, nullable=False)
    asof_time: Mapped[str] = mapped_column(String(8), nullable=False)

    symbol_id: Mapped[int] = mapped_column(
        ForeignKey("symbols.id", ondelete="CASCADE"), nullable=False
    )
    
    instrument_token: Mapped[Optional[str]] = mapped_column(String(16))
    atr_pct: Mapped[Optional[float]] = mapped_column(Numeric(6, 3))
    adv20: Mapped[Optional[float]] = mapped_column(Numeric(18, 2))
    score: Mapped[float] = mapped_column(Numeric(10, 4))
    rank: Mapped[Optional[int]] = mapped_column(Integer)

    # Audit field
    created_at: Mapped[Optional[DateTime]] = mapped_column(DateTime(timezone=True),server_default=func.now())

    symbol: Mapped["Symbol"] = relationship(back_populates="universe_entries")

    __table_args__ = (
        PrimaryKeyConstraint("date", "asof_time", "symbol_id", name="pk_trading_universe"),
        UniqueConstraint("date", "asof_time", "symbol_id", name="uq_universe_snapshot_key"),
        # Fast lookups for intraday consumers
        Index("ix_universe_date_asof_rank", "date", "asof_time", "rank"),
        Index("ix_universe_date_asof_score", "date", "asof_time", "score"),
    )