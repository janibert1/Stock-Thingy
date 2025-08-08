import threading
import time
from datetime import datetime, timedelta
from stockprice import get_stock_price
import pandas as pd

class Simulator:
    def __init__(
        self,
        ticker,
        start_date,
        start_capital=10000,
        threshold_pct=10,
        take_profit_pct=1.5,
        stop_loss_pct=1.0,
        position_size_frac=0.2,
        transaction_cost_pct=0.05,
        max_trades_per_day=1,
        sleep_per_day=1.0,  # seconds per simulated day
    ):
        self.ticker = ticker
        self.current_date = start_date
        self.capital = start_capital
        self.threshold_pct = threshold_pct
        self.take_profit_pct = take_profit_pct
        self.stop_loss_pct = stop_loss_pct
        self.position_size_frac = position_size_frac
        self.transaction_cost_pct = transaction_cost_pct
        self.max_trades_per_day = max_trades_per_day
        self.sleep_per_day = sleep_per_day

        self._stop_event = threading.Event()
        self._thread = None

        self.trade_log = []
        self.last_close_price = None
        self.trades_today = 0

    def start(self):
        if self._thread and self._thread.is_alive():
            print("Simulator already running.")
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

    def stop(self):
        print("Stopping simulator...")
        self._stop_event.set()
        if self._thread:
            self._thread.join()
        print("Simulator stopped.")

    def _run_loop(self):
        print(f"Starting simulation for {self.ticker} from {self.current_date.strftime('%Y-%m-%d')}")
        prev_close = None

        while not self._stop_event.is_set():
            try:
                price = get_stock_price(self.ticker, self.current_date)
            except Exception as e:
                print(f"Error fetching price for {self.current_date.date()}: {e}")
                break

            if prev_close is not None:
                pct_change = (price - prev_close) / prev_close * 100

                # Reset daily trade counter if date changed
                if self.trades_today >= self.max_trades_per_day:
                    # No trades allowed today
                    pass
                else:
                    if abs(pct_change) >= self.threshold_pct:
                        # Determine trade direction
                        direction = "LONG" if pct_change < 0 else "SHORT"
                        position_size = self.capital * self.position_size_frac
                        entry_price = price

                        if direction == "LONG":
                            take_profit_price = entry_price * (1 + self.take_profit_pct / 100)
                            stop_loss_price = entry_price * (1 - self.stop_loss_pct / 100)
                        else:
                            take_profit_price = entry_price * (1 - self.take_profit_pct / 100)
                            stop_loss_price = entry_price * (1 + self.stop_loss_pct / 100)

                        # Simulate trade: assume take profit hit (simplification)
                        realized_return_pct = self.take_profit_pct

                        # Calculate costs (entry + exit)
                        costs = position_size * (self.transaction_cost_pct / 100) * 2

                        profit_loss = position_size * (realized_return_pct / 100) - costs
                        self.capital += profit_loss

                        trade_record = {
                            "Date": self.current_date,
                            "Direction": direction,
                            "Entry_Price": entry_price,
                            "Take_Profit_Price": take_profit_price,
                            "Stop_Loss_Price": stop_loss_price,
                            "Return_%": realized_return_pct,
                            "Costs": costs,
                            "Capital_After_Trade": self.capital,
                        }
                        self.trade_log.append(trade_record)
                        self.trades_today += 1

                        print(
                            f"{self.current_date.date()} - {direction} trade executed. "
                            f"Return: {realized_return_pct:.2f}%, Capital: €{self.capital:,.2f}"
                        )

            else:
                print(f"{self.current_date.date()} - No previous close, skipping trade evaluation.")

            prev_close = price
            self.current_date += timedelta(days=1)
            self.trades_today = 0  # reset trades for next day

            time.sleep(self.sleep_per_day)

        print("Simulation loop ended.")

    def get_trade_log(self):
        return pd.DataFrame(self.trade_log)
