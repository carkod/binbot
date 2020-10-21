# Common Env variables

# General
DEBUG=True
TIMEZONE=US/Eastern
SECRET_KEY=
ENVIRONMENT=development
FLASK_DIRECTORY=/api/
FLASK_DOMAIN=http://localhost
FLASK_PORT=5000
FRONTEND_DOMAIN=http://localhost:3000
HTTP_HTTPS=http://

BASE=https://api.binance.com
# user-data-stream
WS_BASE=wss://stream.binance.com
WS_BASE_PORT=9443

# Database
MONGO_HOSTNAME=localhost
MONGO_PORT=27017
MONGO_AUTH_DATABASE=admin
MONGO_AUTH_USERNAME=root
MONGO_AUTH_PASSWORD=rootpassword
MONGO_APP_DATABASE=binbot

# Binance API URLs

TICKER24=$BASE/api/v1/ticker/24hr
CANDLESTICK=${BASE}/api/v1/klines
TICKER_PRICE=$BASE/api/v3/ticker/price
ACCOUNT=$BASE/api/v3/account
EXCHANGE_INFO=$BASE/api/v1/exchangeInfo
ORDER=$BASE/api/v3/order
OPEN_ORDERS=$BASE/api/v3/openOrders
ALL_ORDERS=$BASE/api/v3/allOrders
AVERAGE_PRICE=$BASE/api/v3/avgPrice
ORDER_BOOK=$BASE/api/v3/depth
WAPI=$BASE/api/v3/depth
WITHDRAW=$BASE/wapi/v3/withdraw.html
DEPOSIT_HISTORY=$BASE/wapi/v3/depositHistory.html
WITHDRAW_HISTORY=$BASE/wapi/v3/withdrawHistory.html
DEPOSIT_ADDRESS=$BASE/wapi/v3/depositAddress.html


# Websockets API
USER_DATA_STREAM=/api/v3/userDataStream

# Binance API limits
MIN_PRICE=0.000001
MIN_QTY=0.001
MIN_NOTIONAL=0.001
RECV_WINDOW=10000

# Binance keys
BINANCE_KEY=ACEO6GUiiTCCKaW33Femziac1h3z3Jw6r1wUwYAPyBkELBYWzpULeA5ZnSEgNWyM
BINANCE_SECRET=msw6Kk43PxCRd385IXNbZPEEGUih3sYYtLTBL2PsIqCwnBa37Kje1ccZvdhLtsGv
EMAIL_ACCOUNT=carkodesign@gmail.com
EMAIL_PASS=48295620-j
SENDER=carkodesign@gmail.com
RECEIVER=carkodw@gmail.com
BINBOARD_DEV_ENV=True
BINBOARD_PROD_ENV=False
BINANCE_WAPI_KEY=BUf8CWHHb24enBQYcn11jRpJD9v01wO3xwqdBiHDhUGmuUUGk0N5GZzfqpx9wwwF
BINANCE_WAPI_SECRET=bXxBxvb8PFEZQPY53S7N50RcBLAE3ZlE9zC9broFxdO9roQUkWfFhrMN5E2NBK9P
BTC_WALLET=35ve2EVmhcjTn3Qmvhz2FdvSwC8ojBXbV6

