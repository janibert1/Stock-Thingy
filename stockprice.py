import yfinance as yf
from datetime import datetime, timedelta
from threading import Thread
from queue import Queue

def get_first_live_price(ticker: str) -> float:

    data = yf.Tickers(ticker).download(
        period='1d',
        interval='1m',
        prepost=True,
        actions=True,
        auto_adjust=True,
        repair=False,
        threads=True,
        group_by='column',
        progress=False,
        timeout=10
    )
    print(data)
    if data.empty or 'Close' not in data.columns:
        raise ValueError(f"No data available for {ticker} on {date.strftime('%Y-%m-%d')}")

    return float(data['Close'].iloc[-1].iloc[0])


def get_stock_price(ticker: str, date: datetime) -> float:
    """
    Fetches the closing stock price for the given ticker and date.
    
    Args:
        ticker (str): Stock ticker symbol (e.g., "MSFT")
        date (datetime): Date for which to fetch the closing price
    
    Returns:
        float: Closing stock price
    """
    # If it's today, grab the first live price
    if date.date() == datetime.now().date():
        return get_first_live_price(ticker)

    # Otherwise, fetch historical closing price
    next_day = date + timedelta(days=1)

    data = yf.Tickers(ticker).download(
        interval='1d',
        start=date,
        end=next_day,
        prepost=False,
        actions=True,
        auto_adjust=True,
        repair=False,
        threads=True,
        group_by='column',
        progress=False,
        timeout=10
    )

    if data.empty or 'Close' not in data.columns:
        raise ValueError(f"No data available for {ticker} on {date.strftime('%Y-%m-%d')}")

    return float(data['Close'].iloc[0].iloc[0])
