# ===================== IMPORTS =====================

import pandas as pd
import numpy as np
import requests
import websocket
import json
import warnings
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier

warnings.filterwarnings("ignore")

# ===================== CONFIG ======================

SYMBOL = "BNBUSDT"

LOOKBACK = 400
TRAIN_WINDOW = 300
RETRAIN_STEP = 50

CONFIDENCE_THRESHOLD = 0.60

model = None
candle_count = 0

df = pd.DataFrame(columns=["Time","Open","High","Low","Close","Volume"])

# ===================== LOAD HISTORICAL DATA =====================

print("Loading historical candles...")

url = f"https://fapi.binance.com/fapi/v1/klines?symbol={SYMBOL}&interval=5m&limit={LOOKBACK}"

data = requests.get(url).json()

rows=[]

for k in data:
    rows.append([
        datetime.fromtimestamp(k[0]/1000),
        float(k[1]),
        float(k[2]),
        float(k[3]),
        float(k[4]),
        float(k[5])
    ])

df=pd.DataFrame(rows,columns=["Time","Open","High","Low","Close","Volume"])

print("Loaded candles:",len(df))

# ===================== INDICATORS =====================

def rsi(series,period=14):

    delta=series.diff()

    gain=(delta.where(delta>0,0)).rolling(period).mean()
    loss=(-delta.where(delta<0,0)).rolling(period).mean()

    rs=gain/loss

    return 100-(100/(1+rs))

def atr(df,length=14):

    tr1=df["High"]-df["Low"]
    tr2=abs(df["High"]-df["Close"].shift())
    tr3=abs(df["Low"]-df["Close"].shift())

    tr=pd.concat([tr1,tr2,tr3],axis=1).max(axis=1)

    return tr.rolling(length).mean()

def vwap(df):

    pv=(df["Close"]*df["Volume"]).cumsum()
    vol=df["Volume"].cumsum()

    return pv/vol

# ===================== FEATURES =====================

def compute_features(df):

    df["Momentum"]=df["Close"].pct_change(5)

    df["ATR"]=atr(df)
    df["ATR_PERCENT"]=df["ATR"]/df["Close"]

    df["RSI"]=rsi(df["Close"])

    df["VWAP"]=vwap(df)

    df["TREND_STRENGTH"]=abs(df["Close"]-df["VWAP"])

    df["VOL_AVG"]=df["Volume"].rolling(20).mean()

    df["VOLUME_SPIKE"]=(df["Volume"]>df["VOL_AVG"]*2).astype(int)

    return df

# ===================== LABELS =====================

def create_labels(df):

    future=df["Close"].shift(-3)

    df["target"]=0

    df.loc[future>df["Close"]*1.002,"target"]=1
    df.loc[future<df["Close"]*0.998,"target"]=-1

    return df

# ===================== TRAIN MODEL =====================

def train_model(df):

    global model

    features=[
        "Momentum",
        "ATR_PERCENT",
        "RSI",
        "TREND_STRENGTH",
        "VOLUME_SPIKE"
    ]

    df=df.dropna()

    X=df[features]
    y=df["target"]

    model=RandomForestClassifier(
        n_estimators=300,
        max_depth=7,
        random_state=42
    )

    model.fit(X,y)

    print("AI model trained")

# ===================== AI SIGNAL =====================

def generate_signal(df):

    if model is None:
        return "HOLD",0

    last=df.iloc[-1]

    X=pd.DataFrame([{

        "Momentum":last["Momentum"],
        "ATR_PERCENT":last["ATR_PERCENT"],
        "RSI":last["RSI"],
        "TREND_STRENGTH":last["TREND_STRENGTH"],
        "VOLUME_SPIKE":last["VOLUME_SPIKE"]

    }])

    probs=model.predict_proba(X)[0]

    prediction=model.predict(X)[0]

    confidence=max(probs)

    if confidence < CONFIDENCE_THRESHOLD:
        return "HOLD",confidence

    if prediction==1:
        return "BUY",confidence

    if prediction==-1:
        return "SELL",confidence

    return "HOLD",confidence

# ===================== MARKET REGIME =====================

def market_regime(df):

    last=df.iloc[-1]

    trend_strength=abs(last["Close"]-last["VWAP"])/last["Close"]

    if trend_strength > 0.002:
        return "TREND"

    return "RANGE"

# ===================== POSITION SIZING =====================

def position_size(balance, atr_percent):

    risk_per_trade=0.01

    position_value=balance*risk_per_trade/atr_percent

    return position_value

# ===================== ANALYSIS =====================

def analyze_market(df):

    signal,confidence=generate_signal(df)

    regime=market_regime(df)

    last=df.iloc[-1]

    if regime=="RANGE":
        signal="HOLD"

    print("\n==============================")
    print("BTCUSDT AI MARKET UPDATE")
    print("==============================")

    print("Time:",last["Time"])
    print("Close:",round(last["Close"],2))

    print("RSI:",round(last["RSI"],2))
    print("ATR %:",round(last["ATR_PERCENT"]*100,3),"%")

    print("VWAP:",round(last["VWAP"],2))

    print("Regime:",regime)

    print("AI Signal:",signal)
    print("Confidence:",round(confidence,2))

    return signal

# ===================== WEBSOCKET =====================

socket=f"wss://fstream.binance.com/ws/{SYMBOL.lower()}@kline_5m"

def on_message(ws,message):

    global df,candle_count

    data=json.loads(message)
    k=data["k"]

    if k["x"]:

        candle={

            "Time":datetime.fromtimestamp(k["t"]/1000),
            "Open":float(k["o"]),
            "High":float(k["h"]),
            "Low":float(k["l"]),
            "Close":float(k["c"]),
            "Volume":float(k["v"])

        }

        df.loc[len(df)]=candle
        df=df.tail(LOOKBACK)

        candle_count+=1

        df=compute_features(df)

        print("\nNew candle closed:",candle["Time"])

        # WALK FORWARD TRAINING

        if len(df)>=TRAIN_WINDOW and candle_count%RETRAIN_STEP==0:

            print("Walk-forward retraining...")

            train_df=df.tail(TRAIN_WINDOW).copy()

            train_df=create_labels(train_df)

            train_model(train_df)

        analyze_market(df)

def on_open(ws):
    print("Connected to Binance kline stream")

ws=websocket.WebSocketApp(
    socket,
    on_message=on_message
)

ws.on_open=on_open
ws.run_forever()