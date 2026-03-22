from kiteconnect import KiteConnect

API_KEY = "3kgmht92u94cowkg"
API_SECRET = "qs5we85barayqa8o9e6lxvn9z5mflsd5"

# https://kite.trade/connect/login?api_key=3kgmht92u94cowkg

# 👇 you will paste this AFTER browser login
REQUEST_TOKEN = "R0JET0HO2tguB7Ud1E2kX1uML1QEuAqZ"

kite = KiteConnect(api_key=API_KEY)

data = kite.generate_session(
    request_token=REQUEST_TOKEN,
    api_secret=API_SECRET
)

access_token = data["access_token"]

print("✅ ACCESS TOKEN GENERATED:")
print(access_token)

# Save token to file
with open("access_token.txt", "w") as f:
    f.write(access_token)
