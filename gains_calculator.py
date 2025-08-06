import json
from decimal import Decimal, getcontext
import datetime
from stockprice import get_stock_price  # This script needs access to this function

# Set precision for financial math
getcontext().prec = 10

def get_gains_and_losses_data(file_path="trade_history.json"):
    """
    Reads trade history, calculates gains/losses, and returns the data as a dictionary.
    """
    try:
        with open(file_path, "r") as f:
            trade_history = json.load(f)
    except (IOError, json.JSONDecodeError):
        # Return a default structure if the file is missing or empty
        return {
            "summary": {
                "total_realized_gains": "0.00",
                "total_unrealized_gains": "0.00",
                "total_combined_gains": "0.00"
            },
            "details": []
        }

    portfolio = {}

    # Aggregate all trades
    for trade in trade_history:
        ticker = trade["ticker"]
        quantity = Decimal(str(trade["quantity"]))
        price = Decimal(str(trade["price"]))
        action = trade["action"].upper()

        if ticker not in portfolio:
            portfolio[ticker] = {
                "shares_bought": Decimal("0"), "total_buy_cost": Decimal("0"),
                "shares_sold": Decimal("0"), "total_sell_revenue": Decimal("0"),
            }

        if action == "BUY":
            portfolio[ticker]["shares_bought"] += quantity
            portfolio[ticker]["total_buy_cost"] += quantity * price
        elif action == "SELL":
            portfolio[ticker]["shares_sold"] += quantity
            portfolio[ticker]["total_sell_revenue"] += quantity * price

    details = []
    total_realized_gains = Decimal("0")
    total_unrealized_gains = Decimal("0")

    # Calculate results for each ticker
    for ticker, data in sorted(portfolio.items()): # Sort by ticker for consistent order
        realized_gain = Decimal("0")
        avg_buy_price = Decimal("0")

        if data["shares_bought"] > 0:
            avg_buy_price = data["total_buy_cost"] / data["shares_bought"]
        
        if data["shares_sold"] > 0:
            cost_of_shares_sold = data["shares_sold"] * avg_buy_price
            realized_gain = data["total_sell_revenue"] - cost_of_shares_sold
            total_realized_gains += realized_gain
        
        unrealized_gain = Decimal("0")
        current_holdings = data["shares_bought"] - data["shares_sold"]
        current_market_value = Decimal("0")
        current_price_str = "N/A"
        
        if current_holdings > 0:
            cost_of_holdings = current_holdings * avg_buy_price
            try:
                # Use your existing function to get live prices
                current_price = Decimal(str(get_stock_price(ticker, datetime.datetime.now())))
                current_price_str = f"{current_price:,.2f}"
                current_market_value = current_holdings * current_price
                unrealized_gain = current_market_value - cost_of_holdings
                total_unrealized_gains += unrealized_gain
            except Exception:
                # Fallback if price fetch fails
                current_price = Decimal("0")

        details.append({
            "ticker": ticker,
            "realized_gains": f"{realized_gain:,.2f}",
            "current_holdings": current_holdings,
            "avg_buy_price": f"{avg_buy_price:,.2f}",
            "current_price": current_price_str,
            "current_market_value": f"{current_market_value:,.2f}",
            "unrealized_gains": f"{unrealized_gain:,.2f}",
        })

    summary = {
        "total_realized_gains": f"{total_realized_gains:,.2f}",
        "total_unrealized_gains": f"{total_unrealized_gains:,.2f}",
        "total_combined_gains": f"{(total_realized_gains + total_unrealized_gains):,.2f}"
    }
    
    return {"summary": summary, "details": details}