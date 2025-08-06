# run_stockprice.py

from datetime import datetime
from stockprice import get_stock_price

# Input values (you can replace with input() calls if needed)
ticker = "aapl"
date_str = "2025-08-05"

# Convert string to datetime
date_obj = datetime.strptime(date_str, "%Y-%m-%d")

# Get and print the price
try:
    price = get_stock_price(ticker, date_obj)
    print(f"{ticker} closing price on {date_str}: {price}")
except ValueError as e:
    print("Error:", e)
