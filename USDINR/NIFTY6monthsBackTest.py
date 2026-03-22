from kiteconnect import KiteConnect
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

# ===================== CONFIG ======================
API_KEY = "3kgmht92u94cowkg"
ACCESS_TOKEN = open("access_token.txt").read().strip()

INDEX_TOKEN = 272643  # NIFTY 50
INTERVAL = "15minute"

JMA_FAST = 14
JMA_SLOW = 34
PHASE = -0.15
POWER = 2

# ===================== INIT ========================
kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

print("⏳ Fetching 6 months data...")

from_date = datetime.now() - timedelta(days=180)

data = kite.historical_data(
    instrument_token=INDEX_TOKEN,
    from_date=from_date,
    to_date=datetime.now(),
    interval=INTERVAL
)

df = pd.DataFrame(data)
df = df[["date", "open", "high", "low", "close"]]
df.columns = ["Time", "Open", "High", "Low", "Close"]
df.reset_index(drop=True, inplace=True)

print(f"✅ Loaded {len(df)} candles")

# ===================== JMA FUNCTION =====================
def jma(series, length, phase, power):
    beta = 0.45 * (length - 1) / (0.45 * (length - 1) + 2)
    alpha = beta ** power

    ma1 = None
    det0 = 0.0
    ma2_prev = None
    det1 = 0.0

    jma_vals = []

    for src in series:
        if ma1 is None:
            ma1 = src
            ma2 = src
            jma_vals.append(src)
            ma2_prev = ma2
            continue

        ma1 = (1 - alpha) * src + alpha * ma1
        det0 = (src - ma1) * (1 - beta) + beta * det0
        ma2 = ma1 + phase * det0
        det1 = ((ma2 - ma2_prev) * ((1 - alpha) ** 2) + (alpha ** 2) * det1)

        jma_vals.append(ma2 + det1)
        ma2_prev = ma2

    return pd.Series(jma_vals)

# ===================== CALCULATE JMA =====================
df["JMA_FAST"] = jma(df["Close"], JMA_FAST, PHASE, POWER)
df["JMA_SLOW"] = jma(df["Close"], JMA_SLOW, PHASE, POWER)

# ===================== BACKTEST =====================
position = None
entry_price = 0
trades = []

for i in range(2, len(df)):

    prev = df.iloc[i-1]
    curr = df.iloc[i]

    buy_signal = prev["JMA_FAST"] < prev["JMA_SLOW"] and curr["JMA_FAST"] > curr["JMA_SLOW"]
    sell_signal = prev["JMA_FAST"] > prev["JMA_SLOW"] and curr["JMA_FAST"] < curr["JMA_SLOW"]

    # ENTRY
    if position is None:
        if buy_signal:
            position = "LONG"
            entry_price = df.iloc[i+1]["Open"] if i+1 < len(df) else curr["Close"]

        elif sell_signal:
            position = "SHORT"
            entry_price = df.iloc[i+1]["Open"] if i+1 < len(df) else curr["Close"]

    # EXIT
    elif position == "LONG" and sell_signal:
        exit_price = df.iloc[i+1]["Open"] if i+1 < len(df) else curr["Close"]
        pnl = exit_price - entry_price
        trades.append(pnl)
        position = None

    elif position == "SHORT" and buy_signal:
        exit_price = df.iloc[i+1]["Open"] if i+1 < len(df) else curr["Close"]
        pnl = entry_price - exit_price
        trades.append(pnl)
        position = None

# ===================== RESULTS =====================
trades = np.array(trades)

total_trades = len(trades)
wins = len(trades[trades > 0])
losses = len(trades[trades <= 0])
win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
total_points = trades.sum()
avg_win = trades[trades > 0].mean() if wins > 0 else 0
avg_loss = trades[trades <= 0].mean() if losses > 0 else 0

# Drawdown
equity = np.cumsum(trades)
peak = np.maximum.accumulate(equity)
drawdown = equity - peak
max_drawdown = drawdown.min() if len(drawdown) > 0 else 0

print("\n================ BACKTEST RESULTS ================")
print(f"Total Trades   : {total_trades}")
print(f"Wins           : {wins}")
print(f"Losses         : {losses}")
print(f"Win Rate       : {win_rate:.2f}%")
print(f"Total Points   : {total_points:.2f}")
print(f"Average Win    : {avg_win:.2f}")
print(f"Average Loss   : {avg_loss:.2f}")
print(f"Max Drawdown   : {max_drawdown:.2f}")
print("==================================================")
