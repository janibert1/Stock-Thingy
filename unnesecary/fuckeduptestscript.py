#!/usr/bin/env python3
import sys
from retreivenews import fetch_news

def main():
    if len(sys.argv) < 2:
        print("Usage: python fetch_news_cli.py <TICKER>")
        sys.exit(1)

    ticker = sys.argv[1].upper()
    files = fetch_news(ticker)

    if files:
        print(f"\nFetched and saved {len(files)} articles for {ticker}:")
        for f in files:
            print(" -", f)
    else:
        print(f"\nNo articles saved for {ticker}.")

if __name__ == "__main__":
    main()
