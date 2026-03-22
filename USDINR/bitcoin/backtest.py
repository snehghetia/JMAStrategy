# ===================== IMPORTS =====================
import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestClassifier

# ===================== CONFIG =====================

SYMBOL = "BNBUSDT"
INTERVAL = "5m"
DAYS_BACK = 30
INITIAL_BALANCE = 100
FEE = 0.0004

# ===================== DOWNLOAD DATA =====================

print("Downloading 30 days of data...")

start_time = int((datetime.now() - timedelta(days=DAYS_BACK)).timestamp() * 1000)

all_rows = []

while True:

    url = "https://fapi.binance.com/fapi/v1/klines"

    params = {
        "symbol": SYMBOL,
        "interval": INTERVAL,
        "limit": 1500,
        "startTime": start_time
    }

    data = requests.get(url, params=params).json()

    if not data:
        break

    for k in data:
        all_rows.append([
            datetime.fromtimestamp(k[0]/1000),
            float(k[1]),
            float(k[2]),
            float(k[3]),
            float(k[4]),
            float(k[5])
        ])

    start_time = data[-1][0] + 1

    print("Downloaded candles:", len(all_rows))

    time.sleep(0.2)

    if len(data) < 1500:
        break


df = pd.DataFrame(all_rows, columns=["Time","Open","High","Low","Close","Volume"])

print("Total candles:", len(df))

# ===================== INDICATORS =====================

def rsi(series,period=14):

    delta = series.diff()

    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()

    rs = gain / loss

    return 100 - (100/(1+rs))


def atr(df,length=14):

    tr1 = df["High"] - df["Low"]
    tr2 = abs(df["High"] - df["Close"].shift())
    tr3 = abs(df["Low"] - df["Close"].shift())

    tr = pd.concat([tr1,tr2,tr3],axis=1).max(axis=1)

    return tr.rolling(length).mean()


def vwap(df):

    pv = (df["Close"] * df["Volume"]).cumsum()
    vol = df["Volume"].cumsum()

    return pv / vol


# ===================== FEATURES =====================

def compute_features(df):

    df["Momentum"] = df["Close"].pct_change(5)

    df["ATR"] = atr(df)
    df["ATR_PERCENT"] = df["ATR"]/df["Close"]

    df["RSI"] = rsi(df["Close"])

    df["VWAP"] = vwap(df)

    df["TREND_STRENGTH"] = abs(df["Close"] - df["VWAP"])

    df["VOL_AVG"] = df["Volume"].rolling(20).mean()

    df["VOLUME_SPIKE"] = (df["Volume"] > df["VOL_AVG"]*2).astype(int)

    return df


# ===================== LABELS =====================

def create_labels(df):

    future = df["Close"].shift(-3)

    df["target"] = 0

    df.loc[future > df["Close"]*1.002,"target"] = 1
    df.loc[future < df["Close"]*0.998,"target"] = -1

    return df


df = compute_features(df)
df = create_labels(df)

df = df.dropna()

features = [
"Momentum",
"ATR_PERCENT",
"RSI",
"TREND_STRENGTH",
"VOLUME_SPIKE"
]

# ===================== TRAIN TEST SPLIT =====================

split = int(len(df)*0.7)

train_df = df[:split]
test_df = df[split:]

X_train = train_df[features]
y_train = train_df["target"]

# ===================== TRAIN MODEL =====================

model = RandomForestClassifier(
n_estimators=300,
max_depth=7,
random_state=42
)

model.fit(X_train,y_train)

print("Model trained")

# ===================== BACKTEST =====================

balance = INITIAL_BALANCE
position = None
entry_price = 0
entry_time = None

wins = 0
losses = 0
trades = 0

trade_log = []

print("\nStarting backtest...\n")

for i in range(len(test_df)):

    row = test_df.iloc[i]

    X = pd.DataFrame([{
        "Momentum": row["Momentum"],
        "ATR_PERCENT": row["ATR_PERCENT"],
        "RSI": row["RSI"],
        "TREND_STRENGTH": row["TREND_STRENGTH"],
        "VOLUME_SPIKE": row["VOLUME_SPIKE"]
    }])

    signal = model.predict(X)[0]

    price = row["Close"]

    if signal == 1:

        if position == "SHORT":

            ret = (entry_price - price)/entry_price
            balance *= (1 + ret - FEE)

            trade_log.append([entry_time,row["Time"],"SHORT",entry_price,price,ret*100])

            trades += 1

            if ret > 0:
                wins += 1
            else:
                losses += 1

        position = "LONG"
        entry_price = price
        entry_time = row["Time"]

    elif signal == -1:

        if position == "LONG":

            ret = (price - entry_price)/entry_price
            balance *= (1 + ret - FEE)

            trade_log.append([entry_time,row["Time"],"LONG",entry_price,price,ret*100])

            trades += 1

            if ret > 0:
                wins += 1
            else:
                losses += 1

        position = "SHORT"
        entry_price = price
        entry_time = row["Time"]

# ===================== RESULTS =====================

print("\n===== BACKTEST RESULTS =====")

print("Trades:", trades)
print("Wins:", wins)
print("Losses:", losses)

if trades > 0:
    print("Win rate:", round(wins/trades*100,2), "%")

print("Final Balance:", round(balance,2))
print("Profit:", round(balance-INITIAL_BALANCE,2))

print("\n===== TRADE LOG =====")

for t in trade_log:

    print(
        "Entry:",t[0],
        "Exit:",t[1],
        "Type:",t[2],
        "EntryPrice:",round(t[3],2),
        "ExitPrice:",round(t[4],2),
        "Return%:",round(t[5],2)
    )