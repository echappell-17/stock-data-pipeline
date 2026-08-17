from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.responses import HTMLResponse
import os
import psycopg2
import psycopg2.extras
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ.get("API_KEY", "stock_task_api_key")

app = FastAPI()

def get_db_connection():
    con = psycopg2.connect(os.environ['DATABASE_URL'])
    return con

def verify_api_key(x_api_key: str = Header(...)):
    # Replace 'your_api_key' with your actual API key
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

def query_prices(ticker: str = 'AAPL',
               start_date: str = None,
               end_date: str = None):

    con = get_db_connection()
    cursor = con.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    query = "SELECT * FROM daily_stock_prices WHERE ticker = %s"
    params = [ticker]

    if start_date:
        query += " AND trade_date >= %s"
        params.append(start_date)
        if end_date:
            query += " AND trade_date <= %s"
            params.append(end_date)

    query += " ORDER BY trade_date"
    cursor.execute(query, params)
    rows = cursor.fetchall()
    cursor.close()
    con.close()

    return [dict(row) for row in rows]

@app.get("/prices")
def get_prices(
        ticker: str = 'AAPL',
        start_date: str = None,
        end_date: str = None,
        x_api_key: None = Depends(verify_api_key)
):
    return query_prices(ticker, start_date, end_date)

@app.get("/prices/table", response_class=HTMLResponse)
def get_prices_table(
        ticker: str = 'AAPL',
        start_date: str = None,
        end_date: str = None
):
    stock_data = query_prices(ticker, start_date, end_date)
    if not stock_data:
        return f'<h3>No data found for {ticker} in the specified date range.</h3>'

    df = pd.DataFrame(stock_data)
    html_table = df.to_html(index=False, classes='table table-striped', border=1)
    return f'''
    <html>
        <head>
            <title>Stock Prices - {ticker}</title>
        </head>
        <body>
            <h1>{ticker} Stock Prices</h1>
            {html_table}
        </body>
    </html>
    '''

@app.get("/")
def root():
    return {'message': 'Stock Data API. Use the /prices/table endpoint to view stock prices.'}