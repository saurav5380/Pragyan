# 0) Scope & Goals

- **Market**: Indian equities (cash market only), NSE/BSE; no F&O; single-locale (IST).
- **APIs**: Zerodha Kite Connect (free tier initially; design for upgrade).
- **Core capabilities**: data ingestion → feature engineering → dynamic universe selection → multi‑strategy ensemble signals → human-in-the-loop alerts → trade journal → backtesting/simulation.
- **Constraints**: free-tier API rate limits, legal/ToS‑compliant news aggregation, runs locally on MacBook M1 Max (Docker) but deployable to cloud later.

---

# 1) High-Level Architecture (Subsystems)

```
┌───────────────────────────────────────────────────────────────────────────┐
│                          CLIENT APPS & INTERFACES                        │
│  Web PWA (React/TS)  │  Mobile (React Native/Expo)  │  CLI/Notebooks     │
└───────────────▲───────────────────────────▲───────────────────────▲───────┘
                │ WebSocket/HTTPS           │ Push (FCM)            │ REST/GRPC
┌───────────────┴───────────────────────────────────────────────────────────┐
│                             APP BACKEND (FastAPI)                         │
│  • API Gateway (Auth, RBAC) • Signal/Journal REST • WebSocket stream      │
│  • Orchestrator endpoints (trigger jobs, backtests, universe builds)      │
└───────────────▲───────────────────────────────────────────────────────────┘
                │                                ▲
                │ RPC/HTTP                       │ Pub/Sub (Redis)
┌───────────────┴──────────┐          ┌──────────┴─────────────────────────┐
│   SCHEDULER & WORKERS     │          │     STREAM & ALERT SERVICE         │
│  Celery + APScheduler     │          │  WebSocket Hub + Push Notifier     │
│  (ingest, features,       │          │  (Expo/FCM + Email)                │
│   signals, backtests)     │          │                                     │
└───────▲─────────────▲─────┘          └─────────▲───────────▲─────────────┘
        │             │                         │           │
        │             │                         │           │
┌───────┴───┐   ┌─────┴──────────────────┐  ┌───┴────────┐  ┌──────────────┐
│  INGEST   │   │  FEATURE ENGINE (TA)   │  │ ENSEMBLE   │  │  BACKTESTER   │
│  (Kite,   │   │  TA/TI + NLP sentiment │  │  (K-of-N)  │  │  (event-driven│
│  News)    │   │  + Entity Linking      │  │  + Risk    │  │   walkforward)│
└────▲──────┘   └──────────▲─────────────┘  └────▲────────┘  └──────▲───────┘
     │                     │                     │                 │
     │                     │                     │                 │
┌────┴───────────────┐ ┌───┴───────────────┐ ┌───┴───────────┐  ┌───┴─────────┐
│   TIMESERIES DB    │ │  OBJECT STORE     │ │   REDIS       │  │  DUCKDB      │
│ Timescale (PGSQL)  │ │ Parquet/S3/MinIO  │ │ cache/rate    │  │ Research/ETL │
│ candles, features, │ │ backtest artifacts│ │ tokens/pubsub │  │ local files  │
│ signals, journal   │ │ & model snapshots │ │ queues        │  │              │
└────────────────────┘ └───────────────────┘ └───────────────┘  └──────────────┘
```

---

# 2) Subsystems, Components, Technologies

## 2.1 Backend API (FastAPI)

- **Purpose**: unified gateway for clients and workers; serves REST & WebSocket.
- **Components**:
  - Auth (JWT), API keys for internal jobs, role-based access (RBAC) if multi-user later.
  - Endpoints: signals, watchlists, symbols, backtest runs, journals, news feed.
  - WebSocket: live signal/price/alert stream to clients.
- **Tech**: FastAPI, Uvicorn, Pydantic v2, SQLAlchemy 2.0, Alembic migrations.

## 2.2 Scheduler & Workers

- **Purpose**: time-based orchestration and heavy lifting.
- **Components**:
  - **APScheduler**: cron-like jobs (e.g., 08:30 IST universe build; 09:00 warm-up scans; periodic feature refreshes; EOD consolidations).
  - **Celery Workers**: task queues for I/O-heavy tasks (ingestion, feature calc, signal eval, backtests). Redis as broker; optional RabbitMQ if scale grows.
- **Tech**: Celery, APScheduler, Redis (broker/result backend), Python 3.11+.

## 2.3 Ingestion Service

- **Market Data**:
  - Zerodha Kite Connect REST for historical candles (1m/3m/5m/15m as allowed).
  - WebSocket (when upgraded) for live ticks, else periodic polling on free tier.
  - Symbol metadata daily refresh from instruments dump.
- **News Aggregation**:
  - RSS/JSON feeds (Moneycontrol, Exchange announcements, Reuters India, etc.) where ToS allow; scrape only where explicitly permitted.
  - De-duplication (hashing), canonicalization, ticker/entity linking.
- **Tech**: httpx (async), feedparser, newspaper3k (opt-in), spaCy/HF for NER; rate-limiters; robots.txt compliance.

## 2.4 Feature Engineering

- **Technical Indicators**: RSI, MACD, ADX, ATR, VWAP deviation, volume z-score, moving averages, ORB ranges, gap %, relative strength vs NIFTY 500.
- **NLP/Sentiment**: FinBERT-like classifier (HF Transformers), novelty scoring (Jaccard/embedding similarity vs 7–30d window), source reliability weights.
- **Feature Store**: persisted to TimescaleDB; incremental updates per bar; opinions (intermediate scores) cached in Redis.
- **Tech**: pandas/polars, pandas-ta, numpy; PyTorch + Transformers; faiss/annoy (optional) for vector similarity.

## 2.5 Universe Selection & Focus Set

- **UniverseScore** = weighted composite of liquidity (ADTV), ATR%, relative strength, trend, premarket gap/vol z-score, news sentiment/novelty.
- **Schedules**:
  - Pre-open (08:30–09:00): compute **Daily Shortlist** (\~100–150).
  - Intraday (every 1–5 min): compute **Focus Set** (20–40) from shortlist based on live signals (VWAP dev, vol z, fresh news).
- **Tech**: Celery tasks, SQL window funcs, Redis sorted sets for top‑K.

## 2.6 Signal Engine (Multi‑Strategy Ensemble)

- **Strategies** (plug-ins):
  - Trend Pullback; VWAP Bounce; Opening Range Breakout; Momentum Convergence (RSI/MACD/ADX); News‑Momentum Confirmation.
- **Outputs per strategy**: bias (buy/sell/none), confidence [0,1], proposed entry/SL/TP, context.
- **Ensemble logic**: K‑of‑N agreement + weighted score threshold; regime adjustment (time-of-day, vol regime).
- **Risk Module**: ATR-based SL/TP, minimum R\:R, position-size hints (non-executing, just guidance).
- **Tech**: Python strategy interfaces; configuration via YAML/JSON; persisted results in Timescale.

## 2.7 Alerting & Delivery

- **Triggers**: Good Signal OR Approaching Entry (|price-entry| <= X%).
- **Channels**: WebSocket to PWA; Push notifications via FCM/Expo; optional email (SES/Postmark).
- **Payload**: order template (symbol, side, entry, SL, TP, validity, qty hint), plus rationale (constituent strategies, news blurb).
- **Tech**: Firebase/Expo; FastAPI WebSocket hub; retry queues in Redis.

## 2.8 Trade Journal & Analytics

- **Journal**: log every signal (even ignored), user actions (placed/modified/skipped), and outcomes (TP/SL, PnL, MAE/MFE).
- **Dashboards**: equity curve, drawdown, hit-rate, per-strategy attribution, hour-of-day analysis.
- **Tech**: Timescale hypertables; Grafana/Metabase for BI; exports to Parquet for notebooks.

## 2.9 Backtesting & Simulation

- **Engine**: event-driven; processes candles in sequence with same strategy code; supports slippage, fees, and execution delay (human latency).
- **Modes**: single symbol, basket/sector, walk-forward (train/test parameter splits), parameter sweeps.
- **Artifacts**: trades CSV, metrics JSON, equity/drawdown PNG/HTML; snapshots stored in object store.
- **Tech**: Python; DuckDB/Polars for fast reads; matplotlib for plots.

## 2.10 Data Stores

- **TimescaleDB (Postgres)**: candles, features, signals, journal, news index.
- **Redis**: caches, rate-limit tokens, pub/sub channels, short-lived signal state.
- **Object Store**: MinIO/S3 for backtest artifacts and model snapshots.
- **Local Files**: Parquet (candles & features) for bulk analysis.

## 2.11 Frontend Apps

- **Web PWA (React + TS + Vite)**:
  - Views: Dashboard (watchlist & focus set), Stock Detail (chart with entry/SL/TP bands + news timeline), Signals Feed, Backtest Lab, Journal.
  - Service Worker: offline cache, push subscription.
  - Live data via WebSocket; secured REST for history.
- **Mobile (React Native/Expo)**:
  - Focused on alerts, quick decision panels, and journal inputs; optional charts.
- **Charts**: Lightweight Charts or Recharts for candlestick + overlays.

## 2.12 Observability & Ops

- **Metrics**: Prometheus (task durations, API latency, signal counts, rate-limit hits).
- **Logs**: OpenSearch/ELK or just structured logs locally; Sentry for error tracking.
- **CI/CD**: GitHub Actions (lint, type-check, unit/integration tests, docker build).

---

# 3) Detailed Data Flows

## 3.1 Morning Universe Build (08:30–09:00 IST)

1. **Fetch instruments** from Kite → store/update `symbols` table.
2. **Load past N days candles** (batched) for all active symbols → `candles` hypertable.
3. **Compute liquidity & volatility**: ADTV (20d), ATR% (14d), spread metrics.
4. **Compute trend & RS**: MA(50/200), RS vs NIFTY 500 (3–12w).
5. **Ingest overnight news**; run NER + sentiment + novelty; map to tickers.
6. **Score** each symbol → `universe_scores` and persist **Daily Shortlist**.

## 3.2 Intraday Loop (market hours)

1. Every **1–5 min**: refresh latest bars for shortlist (batch symbols).
2. Compute **intraday features**: VWAP dev, vol z-score, ORB levels.
3. Select **Focus Set** (top‑K by intraday score; promote/demote based on activity).
4. Run **strategies** only on Focus Set; compute ensemble score.
5. If **Good Signal** or **Approach**: emit alert → push + WebSocket, write `ensemble_signals`.
6. User action on client writes **Trade Intent/Action** into journal.

## 3.3 Backtest Flow

1. User submits backtest params via UI/CLI (symbols, period, strategies, params).
2. Worker loads candles/features from Timescale/DuckDB; runs event loop; simulates latency & slippage.
3. Write results/artifacts to object store + metrics to DB; expose via API for UI.

---

# 4) Core Schemas (first pass)

**symbols**(id PK, exchange, ticker, isin, name, sector, tick\_size, lot\_size\_null, is\_active)

**candles**(symbol\_id, ts, o, h, l, c, v, timeframe, PRIMARY KEY(symbol\_id, ts, timeframe)) -- hypertable

**features**(symbol\_id, ts, rsi14, macd, macd\_sig, adx14, atr14, vwap, vwap\_dev, vol\_z, ma50, ma200, rel\_strength, regime, …)

**news**(id PK, ts, source, url, title, body\_hash, tickers[], sentiment, novelty, reliability)

**universe\_scores**(date, symbol\_id, score, liquidity, atr\_pct, rs, trend, news\_score, gap, volz)

**strategy\_defs**(id PK, name, version, params\_json)

**strategy\_signals**(id PK, ts, symbol\_id, strategy\_id, side, confidence, entry, sl, tp, context\_json)

**ensemble\_signals**(id PK, ts, symbol\_id, side, score, entry, sl, tp, constituents\_json)

**watchlists**(id PK, name)

**watchlist\_items**(watchlist\_id, symbol\_id, preconditions\_json)

**trade\_intents**(id PK, ts, symbol\_id, signal\_id, order\_template\_json)

**trade\_actions**(id PK, intent\_id, action\_ts, action, reason)

**trade\_outcomes**(id PK, intent\_id, exit\_ts, pnl, rr, sl\_hit, tp\_hit, mae, mfe)

---

# 5) Sequence Diagrams (textual)

## 5.1 Signal Generation & Alert (Intraday)

```
Client ──subscribes──> WebSocket Hub
Scheduler ──triggers──> Ingestion (refresh bars/news)
Ingestion ──writes──> Timescale(candles, news)
FeatureEng ──reads──> Timescale(candles) ──writes──> Timescale(features)
UniverseSvc ──reads──> features/news ──writes──> FocusSet (Redis ZSET)
SignalEngine ──reads──> FocusSet + features ──writes──> ensemble_signals
AlertSvc ──reads──> ensemble_signals ──push──> WebSocket/FCM
Client ──sends intent──> API ──writes──> trade_intents/actions
```

## 5.2 Backtest

```
Client ──POST /backtests──> API ──enqueue──> Celery
Worker ──reads──> DuckDB/Timescale ──run sim──> metrics, trades
Worker ──writes──> ObjectStore(artifacts) + Timescale(results)
Client ──GET /backtests/{id}──> API ──returns──> results + links
```

---

# 6) Rate-Limiting & Free-Tier Strategy

- **Token bucket** in Redis per resource (historical candles per minute, instruments refresh, news calls).
- **Batching**: multi-symbol requests where allowed; cache candles in Parquet to avoid repeat downloads.
- **Focus Set** ensures deep calcs on at most 20–40 names per interval.

---

# 7) Security & Compliance

- Kite secrets stored server-side only (env vars or Doppler/Vault); rotated.
- Source allowlist; robots.txt honored; per-source ToS registry; disable scraping otherwise.
- Signed URLs for artifacts; JWT auth for clients; CORS locked to your domains in prod.

---

# 8) Local Development Topology (MacBook M1 Max)

- `docker-compose.yml` services: api(fastapi), worker(celery), scheduler, redis, postgres(timescale), minio, websocket-hub (or within api), grafana(optional).
- Dev conveniences: `make seed` (symbols + sample candles), `make backtest` quick run, hot reload for FastAPI & React.

---

# 9) Initial Parameter Defaults (tunable)

- ADTV threshold: ₹20–50 cr (20d).
- ATR% window 14, keep in [1%, 6%].
- Focus Set size: 30 (±10 based on activity).
- Ensemble: 3-of-5 strategies, score ≥ 0.6, R\:R ≥ 1.5.
- Approaching alert: within 0.3% of entry.

---

# 10) Roadmap (Phased)

- **Phase 0**: Scaffolding + historical ingest + base features + two strategies + alerts + journal + simple backtests.
- **Phase 1**: NLP sentiment + universe scoring + Focus Set + walkforward backtests.
- **Phase 2**: Live WebSocket market data (on upgrade) + regime models + parameter optimizer + richer dashboards.

---

# 11) Tech Choices Summary

- **Backend**: FastAPI, SQLAlchemy, Pydantic, Celery, APScheduler, Redis
- **DB**: TimescaleDB (Postgres), DuckDB/Parquet for research
- **ML**: PyTorch + HF Transformers; pandas/polars + pandas‑ta
- **Frontend**: React + TS (PWA), React Native/Expo (mobile), Lightweight Charts/Recharts
- **Alerts**: WebSocket + FCM/Expo; Email via SES/Postmark
- **Observability**: Prometheus + Grafana; Sentry; Structured JSON logs
- **Packaging**: Docker; GitHub Actions CI

---

# 12) Interfaces (API surface – first pass)

- `POST /universe/build` (admin) – trigger daily build
- `GET /symbols`, `GET /universe/shortlist`, `GET /universe/focus`
- `GET /signals/live` (WebSocket) – subscribe to stream
- `GET /signals/history?symbol=...`
- `POST /watchlists`, `POST /watchlists/{id}/items`
- `POST /backtests` + `GET /backtests/{id}`
- `POST /journal/intents`, `POST /journal/actions`

---

# 13) Testing Strategy

- **Unit tests** for indicators and strategy logic with golden vectors.
- **Property-based tests** for ensemble voting invariants.
- **Snapshot tests** for backtests (metrics shouldn’t drift without code changes).
- **Load tests** for scheduler cadence within free-tier limits.

---

# 14) Open Questions / Config Knobs

- Finalize daily shortlist size & focus set bounds for free tier.
- Exact list of permitted news sources & their ToS.
- Define the five initial strategies’ parameters and stop/target rules.
- Set push notification throttle rules to avoid spam during choppy periods.

