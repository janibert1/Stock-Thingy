# save_live_data.py
import json
import datetime
import os
from portfoliolive import totaltotal

DATA_FILE = "portfolio_live.json"
MAX_DAYS = 7

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return []

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def clean_old_data(data):
    cutoff = datetime.datetime.now() - datetime.timedelta(days=MAX_DAYS)
    return [entry for entry in data if datetime.datetime.fromisoformat(entry["timestamp"]) > cutoff]

def record_portfolio_worth():
    data = load_data()
    current_value = totaltotal()
    timestamp = datetime.datetime.now().isoformat(timespec="seconds")

    # Add new entry
    data.append({
        "timestamp": timestamp,
        "total_worth": current_value
    })

    # Remove old entries
    data = clean_old_data(data)

    save_data(data)

if __name__ == "__main__":
    record_portfolio_worth()
