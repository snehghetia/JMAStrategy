# ===================== IMPORTS =====================
from kiteconnect import KiteConnect, KiteTicker
import pandas as pd
from datetime import datetime, timedelta

last_signal = None

# ===================== CONFIG ======================
API_KEY = "3kgmht92u94cowkg"
ACCESS_TOKEN = open("access_token.txt").read().strip()

USDINR_TOKEN = 272643

INTERVAL_MINUTES = 15        # 15 or 60
LOOKBACK = 50               # 15-min → 50 | 60-min → 120

JMA_FAST = 14
JMA_SLOW = 34
PHASE = -0.15               # SAME scale as Pine (-1 to +1)
POWER = 2
# ==================================================

# ===================== INIT ========================
kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

df = pd.DataFrame(columns=["Time", "Open", "High", "Low", "Close"])
current_candle = None

# ===================== LOAD HISTORICAL DATA =====================
print("⏳ Loading historical candles...")

required = max(LOOKBACK, JMA_SLOW + 2)
days = 10 if INTERVAL_MINUTES == 15 else 20

from_date = datetime.now() - timedelta(days=days)

historical = kite.historical_data(
    instrument_token=USDINR_TOKEN,
    from_date=from_date,
    to_date=datetime.now(),
    interval="15minute" if INTERVAL_MINUTES == 15 else "60minute"
)

hist_df = pd.DataFrame(historical)
hist_df = hist_df[["date", "open", "high", "low", "close"]]
hist_df.columns = ["Time", "Open", "High", "Low", "Close"]

df = hist_df.tail(LOOKBACK).copy()

print(f"✅ Loaded {len(df)} historical candles")

if len(df) < required:
    print(f"⚠️ Warning: Only {len(df)} candles loaded, need {required}")
else:
    print("✅ Sufficient historical data loaded for JMA analysis")

# ===================== PINE-ACCURATE JMA =====================
def jma(series, length, phase, power):
    """
    Pine v6 accurate Jurik Moving Average
    phase range: -1.0 to +1.0
    """

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

        det1 = (
            (ma2 - ma2_prev) * ((1 - alpha) ** 2)
            + (alpha ** 2) * det1
        )

        jma_vals.append(ma2 + det1)
        ma2_prev = ma2

    return pd.Series(jma_vals, index=series.index)

# ===================== ANALYSIS =====================
def analyze_market(df):
    global last_signal

    close = df["Close"]

    df["JMA_FAST"] = jma(close, JMA_FAST, PHASE, POWER)
    df["JMA_SLOW"] = jma(close, JMA_SLOW, PHASE, POWER)

    last = df.iloc[-1]
    prev = df.iloc[-2]

    bias = "Neutral"
    signal = "No Trade"
    new_signal = None

    if prev["JMA_FAST"] < prev["JMA_SLOW"] and last["JMA_FAST"] > last["JMA_SLOW"]:
        new_signal = "BUY"
        bias = "Bullish"

    elif prev["JMA_FAST"] > prev["JMA_SLOW"] and last["JMA_FAST"] < last["JMA_SLOW"]:
        new_signal = "SELL"
        bias = "Bearish"

    # 🔒 Eliminate duplicates
    if new_signal and new_signal != last_signal:
        signal = new_signal
        last_signal = new_signal
    else:
        signal = "No Trade"

    print(f"\n📊 USDINR LIVE {INTERVAL_MINUTES}-MIN JMA UPDATE")
    print(f"Time       : {last['Time']}")
    print(f"Close      : {round(last['Close'], 4)}")
    print(f"JMA Fast   : {round(last['JMA_FAST'], 4)}")
    print(f"JMA Slow   : {round(last['JMA_SLOW'], 4)}")
    print(f"Bias       : {bias}")
    print(f"Signal     : {signal}")
    print("-" * 50)

# ===================== INITIAL HISTORICAL ANALYSIS =====================
if len(df) >= JMA_SLOW + 2:
    print("📌 Last historical signal before live market:")
    analyze_market(df)

# ===================== WEBSOCKET ====================
kws = KiteTicker(API_KEY, ACCESS_TOKEN)

def on_ticks(ws, ticks):
    global current_candle, df

    price = ticks[0]["last_price"]
    now = datetime.now()

    candle_time = now - timedelta(
        minutes=now.minute % INTERVAL_MINUTES,
        seconds=now.second,
        microseconds=now.microsecond
    )

    if current_candle is None or candle_time != current_candle["Time"]:
        if current_candle:
            df.loc[len(df)] = current_candle
            df = df.tail(LOOKBACK)

            if len(df) >= JMA_SLOW + 2:
                analyze_market(df)

        current_candle = {
            "Time": candle_time,
            "Open": price,
            "High": price,
            "Low": price,
            "Close": price
        }
    else:
        current_candle["High"] = max(current_candle["High"], price)
        current_candle["Low"] = min(current_candle["Low"], price)
        current_candle["Close"] = price

def on_connect(ws, response):
    ws.subscribe([USDINR_TOKEN])
    ws.set_mode(ws.MODE_LTP, [USDINR_TOKEN])
    print(f"✅ Connected to USDINR {INTERVAL_MINUTES}-minute JMA live feed")

def on_close(ws, code, reason):
    print("❌ WebSocket closed:", reason)

def on_error(ws, code, reason):
    print("❌ WebSocket ERROR:", code, reason)

kws.on_ticks = on_ticks
kws.on_connect = on_connect
kws.on_close = on_close
kws.on_error = on_error

# ===================== START ========================
print(f"🚀 Starting LIVE USDINR {INTERVAL_MINUTES}-MIN JMA Crossover System...")
kws.connect()
