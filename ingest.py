import os
import psycopg2
import yfinance as yf
from dotenv import load_dotenv

load_dotenv()

# List of stock tickers to ingest
TARGET_TICKERS = ["AAPL"]
# In production this should be managed outside of the code, in a config file or table.

# Define a function to ingest stock data for a given ticker and period
# Defaults to previous day but can be overwritten
def ingest_stock_data(ticker, target_period='1d'):
    stock = yf.Ticker(ticker)
    history = stock.history(period=target_period, interval='1d')  # Fetch daily data for the specified period

    con = psycopg2.connect(os.environ['DATABASE_URL'])
    cursor = con.cursor()
    for _, row in history.iterrows():
        cursor.execute('''
            INSERT INTO daily_stock_prices (ticker, trade_date, open_price, close_price, high_price, low_price, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (ticker, trade_date) DO UPDATE SET
                open_price = EXCLUDED.open_price,
                high_price = EXCLUDED.high_price,
                low_price = EXCLUDED.low_price,
                close_price = EXCLUDED.close_price,
                volume = EXCLUDED.volume,
                fetched_at = CURRENT_TIMESTAMP
        ''', (ticker,
              row.name.date(),
              float(row['Open']),
              float(row['Close']),
              float(row['High']),
              float(row['Low']),
              int(row['Volume'])
        ))
    con.commit()
    cursor.close()
    con.close()
    print(f"Data for {ticker} stored successfully.")


#   When the script is run directly, ingest data for the previous 5 years
if __name__ == "__main__":
    for ticker in TARGET_TICKERS:
        # Fetch and store daily data for previous 5 years
        ingest_stock_data(ticker, target_period="5y")