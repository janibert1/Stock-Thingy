#!/usr/bin/env python3
import sys
import json
import os
from datetime import datetime
from stockprice import get_stock_price  # Import your existing function

PORTFOLIO_FILE = "portfolio.json"
TRADE_HISTORY_FILE = "trade_history.json"

# ---------------------- Portfolio ----------------------

def load_portfolio():
    if not os.path.exists(PORTFOLIO_FILE):
        return []
    with open(PORTFOLIO_FILE, "r") as f:
        return json.load(f)

def save_portfolio(portfolio):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(portfolio, f, indent=4)

# ---------------------- Trade History ----------------------

def load_trade_history():
    if not os.path.exists(TRADE_HISTORY_FILE):
        return []
    with open(TRADE_HISTORY_FILE, "r") as f:
        return json.load(f)

def save_trade_history(history):
    with open(TRADE_HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=4)

def log_trade(action, ticker, quantity, price):
    history = load_trade_history()
    history.append({
        "action": action,
        "ticker": ticker,
        "quantity": quantity,
        "price": price,
        "timestamp": datetime.now().isoformat()
    })
    save_trade_history(history)

# ---------------------- Actions ----------------------

def buy_stock(ticker, quantity):
    timestamp = datetime.now()
    price = get_stock_price(ticker, timestamp)
    
    # Update portfolio
    portfolio = load_portfolio()
    portfolio.append({
        "ticker": ticker.upper(),
        "quantity": quantity,
        "price": price,
        "timestamp": timestamp.isoformat()
    })
    save_portfolio(portfolio)

    # Log trade
    log_trade("BUY", ticker.upper(), quantity, price)
    
    print(f"Bought {quantity} share(s) of {ticker.upper()} at ${price:.2f} each.")

def sell_stock(ticker, quantity):
    portfolio = load_portfolio()
    ticker = ticker.upper()
    
    # Filter out only this ticker's stocks
    owned_stocks = [s for s in portfolio if s["ticker"] == ticker]
    if sum(s["quantity"] for s in owned_stocks) < quantity:
        print(f"Not enough shares of {ticker} to sell.")
        return

    # FIFO selling
    remaining = quantity
    new_portfolio = []
    for stock in portfolio:
        if stock["ticker"] == ticker and remaining > 0:
            if stock["quantity"] <= remaining:
                remaining -= stock["quantity"]
                # fully sold, don't add back
            else:
                stock["quantity"] -= remaining
                remaining = 0
                new_portfolio.append(stock)
        else:
            new_portfolio.append(stock)

    save_portfolio(new_portfolio)

    # Fetch live price for sell
    price = get_stock_price(ticker, datetime.now())

    # Log trade
    log_trade("SELL", ticker, quantity, price)

    print(f"Sold {quantity} share(s) of {ticker} at ${price:.2f} each.")

# ---------------------- Main ----------------------

def main():
    if len(sys.argv) < 4:
        print("Usage: stocky.py [buy|sell] TICKER QUANTITY")
        sys.exit(1)

    action = sys.argv[1].lower()
    ticker = sys.argv[2]
    quantity = int(sys.argv[3])

    if action == "buy":
        buy_stock(ticker, quantity)
    elif action == "sell":
        sell_stock(ticker, quantity)
    else:
        print("Invalid action. Use 'buy' or 'sell'.")

if __name__ == "__main__":
    main()
