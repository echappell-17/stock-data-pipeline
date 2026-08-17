from ingest import ingest_stock_data, TARGET_TICKERS

if __name__ == "__main__":
    for ticker in TARGET_TICKERS:
        # Fetch and store data for the previous day
        ingest_stock_data(ticker)