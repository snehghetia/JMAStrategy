from kiteconnect import KiteConnect
from datetime import datetime

API_KEY = "3kgmht92u94cowkg"
ACCESS_TOKEN = "M1fYOKpH7KmZDbsbD2L94Xu3LCZj6mOl"

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

current_month = datetime.now().strftime("%b").upper()

instruments = kite.instruments("CDS")

for i in instruments:
    if (
        "USDINR" in i["tradingsymbol"]
        and i["instrument_type"] == "FUT"
        and current_month in i["tradingsymbol"]
    ):
        print("CURRENT MONTH USDINR:")
        print("Symbol :", i["tradingsymbol"])
        print("Token  :", i["instrument_token"])