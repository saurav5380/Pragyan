from alembic import op

def upgrade():
    op.execute("""
        CREATE MATERIALIZED VIEW mv_focus_base AS
        SELECT tu.symbol_id,
               tu.rank AS universe_rank,
               f.ts,
               f.vwap_dev_pct,
               f.vol_z,
               f.orb_status
        FROM trade_universe tu
        JOIN features f
          ON tu.symbol_id = f.symbol_id
         AND f.ts = (SELECT MAX(ts) FROM features f2 WHERE f2.symbol_id = f.symbol_id)
        WHERE tu.date = CURRENT_DATE;
    """)
    # optional: unique index so you can REFRESH CONCURRENTLY
    op.execute("CREATE UNIQUE INDEX ON mv_focus_base (symbol_id);")

def downgrade():
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_focus_base;")
