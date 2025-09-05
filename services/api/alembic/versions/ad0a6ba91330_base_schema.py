"""base schema

Revision ID: ad0a6ba91330
Revises: 
Create Date: 2025-08-22 11:15:17.859871

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ad0a6ba91330'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "symbols",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("exchange", sa.String(8), nullable=False),
        sa.Column("ticker", sa.String(32), nullable=False),
        sa.Column("name", sa.String(64), nullable=True),
        sa.Column("sector", sa.String(128), nullable=True),
        sa.Column("tick_size", sa.Numeric(10,4), nullable=True),
        sa.Column("instrument_token", sa.String(16), nullable=False),
        sa.Column("last_price", sa.Numeric(10,4), nullable=False),
        # sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.UniqueConstraint("exchange","ticker", name="uq_symbols_exchange_ticker"),
    )

    op.create_table(
        "candles",
        sa.Column("symbol_id", sa.Integer, sa.ForeignKey("symbols.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ts", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("o", sa.Numeric(14,4), nullable=False),
        sa.Column("c", sa.Numeric(14,4), nullable=False),
        sa.Column("h", sa.Numeric(14,4), nullable=False),
        sa.Column("l", sa.Numeric(14,4), nullable=False),
        sa.Column("v", sa.BigInteger, nullable=False),
        sa.Column("timeframe", sa.String(8), nullable=False),
        sa.PrimaryKeyConstraint("symbol_id", "ts", "timeframe", name="pk_candles")
    )
    # creating hypertable
    # op.execute("SELECT create_hypertable('candles','ts');")

    #create index on table candles to improve search speed
    op.create_index("ix_candles_symbol_ts", "candles", ["symbol_id", "ts"])

    op.create_table(
        "features",
        sa.Column("symbol_id", sa.Integer, sa.ForeignKey("symbols.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ts", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("rsi14", sa.Numeric(6,3), nullable=True),
        sa.Column("macd", sa.Numeric(10,4), nullable=True),
        sa.Column("macd_sig", sa.Numeric(10,4), nullable=True),
        sa.Column("atr14", sa.Numeric(10,4), nullable=True),
        sa.Column("vwap", sa.Numeric(10,4), nullable=True),
        sa.Column("vwap_dev", sa.Numeric(10,4), nullable=True),
        sa.Column("vol_z", sa.Numeric(10,4), nullable=True),
        sa.Column("ma50", sa.Numeric(14,4), nullable=True),
        sa.Column("ma200", sa.Numeric(14,4), nullable=True),
        sa.PrimaryKeyConstraint("symbol_id","ts",name="pk_features"),
    )

    #create index on features table
    op.create_index("idx_features_symbol_ts", "features", ["symbol_id", "ts"])

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_features_symbol_ts",table_name="features")
    op.drop_table("features")
    op.drop_index("ix_candles_symbol_ts", table_name="candles")
    op.drop_table("candles")
    op.drop_table("symbols")


