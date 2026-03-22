from kiteconnect import KiteConnect

API_KEY = "3kgmht92u94cowkg"
ACCESS_TOKEN = open("access_token.txt").read().strip()

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

try:
    print(kite.profile())
    print("✅ AUTH OK")
except Exception as e:
    print("❌ AUTH FAILED:", e)
