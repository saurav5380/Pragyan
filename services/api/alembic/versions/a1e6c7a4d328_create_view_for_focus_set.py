"""create view for focus set

Revision ID: a1e6c7a4d328
Revises: 287668a39ac8
Create Date: 2025-09-28 19:27:33.837418

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1e6c7a4d328'
down_revision: Union[str, Sequence[str], None] = '287668a39ac8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE MATERIALIZED VIEW mv_focus_base AS
        SELECT tu.symbol_id,
               tu.rank AS universe_rank,
               f.ts,
               f.vwap_dev,
               f.vol_z
        FROM trading_universe tu
        JOIN features f
          ON tu.symbol_id = f.symbol_id
         AND f.ts = (SELECT MAX(ts) FROM features f2 WHERE f2.symbol_id = f.symbol_id)
        WHERE tu.date = CURRENT_DATE;
    """)
    # unique index so you can REFRESH CONCURRENTLY
    op.execute("CREATE UNIQUE INDEX ON mv_focus_base (symbol_id);")

def downgrade() -> None:
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_focus_base;")