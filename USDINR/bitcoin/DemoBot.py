import time
import pandas as pd
from binance.client import Client
from BitcoinJMA import generate_signal

API_KEY = "6jKaDHroqt8qJaQlpWn6dtJPlNSMa724gzi5Bxar49kewihi1fjSMXU8KGDG58Vd"
API_SECRET = "i6GRDMxuPsHuntVvnWBQeljiVtFWQhqcrmQlpHhP7vsnO0k8eapmIpuj6WhYuHOG"

SYMBOL = "BNBUSDT"
INTERVAL = Client.KLINE_INTERVAL_5MINUTE
TRADE_SIZE = 0.01

client = Client(API_KEY, API_SECRET)

# demo futures endpoint
client.FUTURES_URL = "https://demo-fapi.binance.com/fapi"

# set leverage
client.futures_change_leverage(symbol=SYMBOL, leverage=5)


def get_candles():

    klines = client.futures_klines(
        symbol=SYMBOL,
        interval=INTERVAL,
        limit=100
    )

    df = pd.DataFrame(klines)

    df = df[[0,4]]
    df.columns = ["time","close"]

    df["close"] = df["close"].astype(float)

    return df


def get_position():

    positions = client.futures_position_information(symbol=SYMBOL)

    for p in positions:
        if float(p["positionAmt"]) != 0:
            return float(p["positionAmt"])

    return 0


def place_buy():

    print("Placing BUY order")

    order = client.futures_create_order(
        symbol=SYMBOL,
        side="BUY",
        type="MARKET",
        quantity=TRADE_SIZE
    )

    print(order)


def place_sell():

    print("Placing SELL order")

    order = client.futures_create_order(
        symbol=SYMBOL,
        side="SELL",
        type="MARKET",
        quantity=TRADE_SIZE
    )

    print(order)


print("BOT STARTED")

while True:

    try:

        df = get_candles()

        signal = generate_signal(df)

        position = get_position()

        print("Signal:", signal)
        print("Position:", position)

        if signal == "BUY" and position <= 0:
            place_buy()

        elif signal == "SELL" and position >= 0:
            place_sell()

        else:
            print("No trade")

    except Exception as e:
        print("Error:", e)

    time.sleep(300)