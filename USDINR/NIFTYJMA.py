# ===================== IMPORTS =====================
from kiteconnect import KiteConnect, KiteTicker
import pandas as pd
from datetime import datetime, timedelta

# ===================== CONFIG ======================
API_KEY = "API_KEY"
ACCESS_TOKEN = open("access_token.txt").read().strip()

INDEX_TOKEN = 256265  # NIFTY 50
INTERVAL_MINUTES = 15
LOOKBACK = 120

JMA_FAST = 14
JMA_SLOW = 34
PHASE = -0.15
POWER = 2

OTM_DISTANCE = 100

# ===================== INIT ========================
kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

df = pd.DataFrame(columns=["Time", "Open", "High", "Low", "Close"])
current_candle = None

# ===================== LOAD HISTORICAL =====================
print("⏳ Loading historical candles...")

from_date = datetime.now() - timedelta(days=10)

historical = kite.historical_data(
    instrument_token=INDEX_TOKEN,
    from_date=from_date,
    to_date=datetime.now(),
    interval="15minute"
)

hist_df = pd.DataFrame(historical)
hist_df = hist_df[["date", "open", "high", "low", "close"]]
hist_df.columns = ["Time", "Open", "High", "Low", "Close"]

hist_df["Time"] = pd.to_datetime(hist_df["Time"]).dt.tz_localize(None)
df = hist_df.tail(LOOKBACK).copy()

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

    return pd.Series(jma_vals, index=series.index)

# ===================== ANALYSIS =====================
def analyze_market(df, ltp):

    close = df["Close"]

    df["JMA_FAST"] = jma(close, JMA_FAST, PHASE, POWER)
    df["JMA_SLOW"] = jma(close, JMA_SLOW, PHASE, POWER)

    last = df.iloc[-1]

    # TREND STATE SIGNAL
    if last["JMA_FAST"] > last["JMA_SLOW"]:
        signal = "BUY"
    elif last["JMA_FAST"] < last["JMA_SLOW"]:
        signal = "SELL"
    else:
        signal = "NEUTRAL"

    atm = round(ltp / 50) * 50

    if signal == "BUY":
        strike = atm + OTM_DISTANCE
        option_type = "CE"
    elif signal == "SELL":
        strike = atm - OTM_DISTANCE
        option_type = "PE"
    else:
        strike = None
        option_type = None

    print("\n" + "="*60)
    print(f"📊 NIFTY {INTERVAL_MINUTES} MIN JMA STATUS")
    print(f"Candle Closed : {last['Time']}")
    print(f"NIFTY LTP     : {ltp}")
    print(f"Signal        : {signal}")

    if strike:
        print(f"OTM Strike    : {strike} {option_type}")

    print("="*60)
    print(f"JMA_FAST: {last['JMA_FAST']:.2f} | JMA_SLOW: {last['JMA_SLOW']:.2f}")

# ===================== WEBSOCKET =====================
kws = KiteTicker(API_KEY, ACCESS_TOKEN)

def on_ticks(ws, ticks):
    global current_candle, df

    tick = ticks[0]
    price = tick["last_price"]
    now = tick["exchange_timestamp"].replace(tzinfo=None)

    candle_time = now - timedelta(
        minutes=now.minute % INTERVAL_MINUTES,
        seconds=now.second,
        microseconds=now.microsecond
    )

    # New candle started → previous candle closed
    if current_candle is None or candle_time != current_candle["Time"]:

        if current_candle:
            df.loc[len(df)] = current_candle
            df = df.tail(LOOKBACK)

            print(f"\n🕒 15-min Candle Closed at {current_candle['Time']}")

            if len(df) >= JMA_SLOW + 2:
                analyze_market(df, current_candle["Close"])

        # Start new candle
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
    ws.subscribe([INDEX_TOKEN])
    ws.set_mode(ws.MODE_FULL, [INDEX_TOKEN])
    print("✅ Connected to NIFTY live feed")

def on_error(ws, code, reason):
    print(f"❌ WebSocket Error: {code} | {reason}")

def on_close(ws, code, reason):
    print("🔴 WebSocket Closed")

kws.on_ticks = on_ticks
kws.on_connect = on_connect
kws.on_error = on_error
kws.on_close = on_close

print("🚀 Starting NIFTY 15-Min JMA Signal System...")
kws.connect()
