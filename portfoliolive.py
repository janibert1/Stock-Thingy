import json
from stockprice import get_stock_price
import datetime
def total_worth():
    with open("portfolio.json", "r") as f:
        portfolio = json.load(f)

    # Calculate total worth
    total_worth = sum(stock["quantity"] * stock["price"] for stock in portfolio)
    return total_worth

def total_current_worth():
    with open("portfolio.json", "r") as f:
        portfolio = json.load(f)
    total_value = sum(get_stock_price(stock["ticker"], datetime.datetime.now()) * stock["quantity"] for stock in portfolio)
    return total_value

def totaltotal():
    final = total_current_worth() - total_worth()
    return final



if __name__ == "__main__":
    totaltotal()


