
import sys
import os
import subprocess
import json
from datetime import datetime
from stocky import load_portfolio, buy_stock, sell_stock
from google import genai
from retreivenews import fetch_news
from stockprice import get_stock_price
from datetime import datetime


# --- Gemini Setup ---
client = genai.Client()  # Requires GEMINI_API_KEY set

# --- Config ---
ARTICLES_DIR = "articles"




def summarize_and_advise(ticker: str):
    """Reads news articles and gets a Buy/Hold/Sell advice from Gemini."""
    articles = []
    for filename in os.listdir(ARTICLES_DIR):
        if filename.endswith(".txt"):
            with open(os.path.join(ARTICLES_DIR, filename), 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    articles.append(content)

    if not articles:
        print("No articles found for analysis.")
        return "hold"

    combined_news = "\n\n".join(articles[:5])  # Limit to first 5 for token efficiency
    portfolio = load_portfolio()
    prompt = f"""
    You are an AI stock advisor.
    Analyze the following recent news about {ticker} and provide one of three advices:
    1. "buy" - if the stock is likely to rise soon
    2. "hold" - if the stock should be kept as is
    3. "sell" - if the stock is likely to fall

    Only output one word: buy, hold, or sell.
    You currently own {sum(item["quantity"] for item in portfolio if item["ticker"] == ticker)} of {ticker} with an average buy price of {(sum(item["price"] * item["quantity"] for item in portfolio if item["ticker"] == ticker))/sum(item["quantity"] for item in portfolio if item["ticker"] == ticker)}. The current price is {get_stock_price(ticker, datetime.now())}
    News:
    {combined_news}
    """
    print(
        f"You currently own {sum(item['quantity'] for item in portfolio if item['ticker'] == ticker)} of {ticker} "
        f"with an average buy price of "
        f"{(sum(item['price'] * item['quantity'] for item in portfolio if item['ticker'] == ticker)) / sum(item['quantity'] for item in portfolio if item['ticker'] == ticker):.2f}. "
        f"The current price is {get_stock_price(ticker, datetime.now())}"
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt
    )
    advice = response.text.strip().lower()
    if advice not in ["buy", "hold", "sell"]:
        advice = "hold"
    return advice

def main():
    if len(sys.argv) < 2:
        print("Usage: aistock.py TICKER")
        sys.exit(1)

    ticker = sys.argv[1].upper()

    # Step 1: Fetch news
    fetch_news(ticker)
    print("hello")
    # Step 2: Get AI advice
    advice = summarize_and_advise(ticker)
    print(f"\nAI Advice for {ticker}: {advice.upper()}")

    # Step 3: Check portfolio for context
    portfolio = load_portfolio()
    owned_quantity = sum(item["quantity"] for item in portfolio if item["ticker"] == ticker)
    print(f"Currently holding {owned_quantity} shares of {ticker}.")

    # Step 4: Confirm execution
    if advice == "sell" and owned_quantity == 0:
        print("Cannot sell, no shares owned.")
        return

    confirm = input(f"Do you want to execute this action ({advice})? [yes/no]: ").strip().lower()
    if confirm != "yes":
        print("Action canceled.")
        return

    # Step 5: Execute trade
    if advice == "buy":
        qty = int(input("How many shares to buy?: "))
        buy_stock(ticker, qty)
    elif advice == "sell":
        qty = int(input(f"How many shares to sell? (max {owned_quantity}): "))
        sell_stock(ticker, min(qty, owned_quantity))
    else:
        print("Holding. No action executed.")

if __name__ == "__main__":
    main()