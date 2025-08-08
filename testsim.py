import datetime
import simulation as sm

sim = sm.Simulator(
    ticker="AAPL",
    start_date=datetime.datetime(2023, 1, 1),
    start_capital=10000,
    threshold_pct=10,
    take_profit_pct=1.5,
    stop_loss_pct=1.0,
    position_size_frac=0.2,
    transaction_cost_pct=0.05,
    max_trades_per_day=1,
    sleep_per_day=0.5  # halve seconde per dag in simulatie
)

sim.start()

# Laat het lopen een tijdje (bv. 10 seconden)
import time
time.sleep(10)

sim.stop()

df = sim.get_trade_log()
print(df)
