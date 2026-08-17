import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    return psycopg2.connect(os.environ["DATABASE_URL"])

def initialise_stocks_database():
    con = get_db_connection()
    cursor = con.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_stock_prices (
            ticker TEXT NOT NULL,
            trade_date DATE NOT NULL,
            open_price DECIMAL(20,6) NOT NULL,
            high_price DECIMAL(20,6) NOT NULL,
            low_price DECIMAL(20,6) NOT NULL,
            close_price DECIMAL(20,6) NOT NULL,
            volume INTEGER NOT NULL,
            fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY(ticker, trade_date)
        )
    ''')

    con.commit()
    cursor.close()
    con.close()


if __name__ == "__main__":
    initialise_stocks_database()
    print("Database initialized and table created.")