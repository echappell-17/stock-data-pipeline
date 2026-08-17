# Stock Data Pipeline

A small end-to-end pipeline that fetches Apple (AAPL) stock data via `yfinance`,
stores it in a PostgreSQL database, and serves it through a FastAPI endpoint (JSON + HTML table).
Containerised with Docker, with GitHub Actions workflows for automated deployment and scheduled daily ingestion.

---

## 1. Overview

- **Data Ingestion:** `ingest.py` pulls daily open, close, high, low and volume data for AAPL from Yahoo Finance via the `yfinance` library.
- **Data Storage:** Data is stored in a PostgreSQL database hosted on Neon, one row per ticker/trade_date.
- **Display Layer:** `app.py` (FastAPI) exposes the data as JSON (`/prices`, API-key protected) and as an HTML table (`/prices/table`).
- **Deployment:** A `Dockerfile` packages the app; GitHub Actions builds the image on every push and runs ingestion daily to get the latest data.

This combination was chosen based on simplicity whilst meeting the requirements of the task. The initial choice was to use SQLite as the database, but I revisited this when I required a persistent database without having to commit changes.

---

## 2. Architecture

```
yfinance API
     │
     ▼
ingest.py / daily_ingest.py  ──►  daily_stock_prices (PostgreSQL)
                                        │
                                        ▼
                                    app.py (FastAPI)
                                    ├── GET /prices        (JSON, API-key auth)
                                    └── GET /prices/table  (HTML table)
```

**Components:**

| File | Responsibility |
|---|---|
| `initialise_database.py` | Creates the `daily_stock_prices` table if it doesn't exist |
| `ingest.py` | Fetches historical/daily data from `yfinance` and upserts into PostgreSQL|
| `daily_ingest.py` | Thin wrapper that runs `ingest_stock_data()` for each ticker in `TARGET_TICKERS`, used by the scheduled job |
| `app.py` | FastAPI app serving `/prices` (JSON) and `/prices/table` (HTML) |
| `Dockerfile` | Containerises the FastAPI app |
| `.github/workflows/docker_build.yml` | Builds the Docker image on push/PR to `main` |
| `.github/workflows/daily_ingest.yml` | Scheduled job - runs daily to ingest latest data|

---

## 3. Data Ingestion

- `ingest.py` defines the list of target tickers, for which the following ingestion steps retrieve data. In production this would need to be managed outside the code, in a config file or an environment variable. It currently only includes AAPL.
- `ingest.py` defines the function `ingest_stock_data`, which takes a ticker and a period as parameters and inserts the daily OHLCV data for the specified parameters into the `daily_stock_prices` table.
- `daily_ingest.py` imports `ingest_stock_data` from `ingest.py` and uses it to load data from the previous day for each of the target tickers.
- `daily_ingest.yml` is a scheduled GitHub workflow which runs `daily_ingest.py` to keep data up to date for the target tickers

yfinance was chosen because it doesn’t require any signup or API key. This meant accepting that yfinance is unofficial so there is no guarantee that it will be maintained. At production scale a more reliable option such as Finnhub or Massive should be chosen depending on budget and requirements.
---

## 4. Data Storage

```sql
CREATE TABLE IF NOT EXISTS daily_stock_prices (
    ticker TEXT NOT NULL,
    trade_date DATE NOT NULL,
    open_price NUMERIC(20,6) NOT NULL,
    close_price NUMERIC(20,6) NOT NULL,
    high_price NUMERIC(20,6) NOT NULL,
    low_price NUMERIC(20,6) NOT NULL,
    volume INTEGER NOT NULL,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(ticker, trade_date)
);
```

**Why this structure:**

- **Composite primary key `(ticker, trade_date)`**: Prevents duplicate records from being created. Running the ingest script again updates records.
- **`fetched_at` timestamp**: records when a row was last updated, useful for auditing the scheduled job.
- **Flat, single-table design**: appropriate to contain daily OHLCV data for a small number of tickers. At a larger scale a dimension table for the tickers could be added.
- **PostgreSQL**: Persistent database, performs well at large scales and can handle concurrent writes.

I started out with a SQLite database for ease of setup and use with Python, but decided to change because data didn’t persist across deployments without committing any recently ingested data to the repository.

The switch to PostgreSQL solved this issue, and came with the added benefits of scalability, and ability to handle concurrent writes from multiple users, which would become useful in a production level.

PostgreSQL could be seen as overkill for an app of this size, but I decided it was worth the extra setup and management of connection strings once I hit the issue of having to commit ingested data.

---

## 5. Display Layer

- FastAPI app serves data in two outputs.
- API-key-protected JSON endpoint at `/prices`, with optional `ticker`, `start_date`, `end_date` filters.
- Unauthenticated HTML table view at `/prices/table` for quick manual inspection. Deliberately left unauthenticated so that the data can be viewed from a normal browser url visit.
- For a production environment, the API key could be replaced by OAuth, this would allow both outputs to be authenticated, and also gains the additional benefits of OAuth (per-user identities, narrower permissions and expiring tokens)
- API only returns data which is already ingested to the database. For additional tickers or dates outside the loaded range nothing will be returned. A possible improvement could be to import ‘ingest.py’ into ‘app.py’ and then call the ‘ingest_stock_data’ function to ingest the additional data on request.

---

## 6. What Works

- End-to-end flow: fetch → store → serve for AAPL.
- Ingestion is safe to re-run without creating duplicate rows.
- Dockerfile builds and runs the app successfully.
- GitHub Actions:
  - `docker_build.yml` verifies the image builds on every push/PR to `main`.
  - `daily_ingest.yml` runs ingestion on a daily schedule (`workflow_dispatch` also allows manual runs).
- Web service hosted on Render redeploys on push to the main branch.

---

## 7. What Doesn't Work / Known Limitations

- **Only one ticker is configured** - (`TARGET_TICKERS = ["AAPL"]`), and `/prices` can only query tickers already present in the database - there's no on-demand fetch-any-ticker capability.
- **No automated tests** - nothing verifies ingestion or API behaviour outside of manual checks.
- **Default API key fallback** - `API_KEY` defaults to a plaintext value (`stock_task_api_key`) if the environment variable isn't set. This is just a default for the demo, not a practice for production.
- **No rate limiting** on `/prices`, which would be needed at real scale.
- **Date filters on API endpoint** only apply if a filter is also applied to the ticker, and ‘end_date’ can only be used if ‘start_date’ is included.

---

## 8. How to Run

### Local (no Docker)

```bash
pip install -r requirements.txt
python initialise_database.py
python ingest.py            # backfills 5 years of history
# or: python daily_ingest.py   # fetches only the most recent day
fastapi run app.py
```

Then visit:
- `http://localhost:8000/` — health check
- `http://localhost:8000/prices/table` - HTML table view
- `http://localhost:8000/prices` - JSON (requires `X-API-Key` header)

### Docker

```bash
docker build -t stock_data_pipeline .
docker run -p 8000:8000 stock_data_pipeline
```
### Render

- Connect GitHub repository in Render
- Render watches for change to main branch
- Upon each change Render redeploys the app
- Available at:
 - `https://stock-data-pipeline-qlf6.onrender.com/prices/table` - HTML table view
 - `https://stock-data-pipeline-qlf6.onrender.com/prices` - JSON output (with API key)

### Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `API_KEY` | Required in the `X-API-Key` header for `/prices` | `stock_task_api_key` (insecure fallback) |
| `DATABASE_URL` | Required to connect to the PostgreSQL database | postgresql://username:password@host/dbname?sslmode=require |

### CI/CD

- **`docker_build.yml`:** builds the Docker image on every push/PR to `main` as a sanity check (build-only, no deploy step).
- **Render webhooks** check for changes to the main branch and redeploy the web service.

Although the docker build workflow checks that the Docker image builds correctly, there is no verification of the data being returned by the API.

---

## 9. Improvements With More Time

- **Multi-ticker support:** Parameterise the ticker list via config/env rather than hardcoding
  `TARGET_TICKERS`.
- **On-demand fetch:** Allow /prices to trigger an on-demand fetch for tickers or date ranges not yet stored in the database.
- **Testing:** Add test scripts to validate ingestion scripts and the API endpoint.
- **Authorisation:** Use OAuth instead of an API key to authorise the visual endpoint /Prices/Table as well as the JSON endpoint /Prices.


