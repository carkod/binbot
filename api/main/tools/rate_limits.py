import os
import requests
from dotenv import load_dotenv

load_dotenv()
info_url = os.getenv("BASE") + os.getenv("EXCHANGE_INFO")

def order_rate_limit(pair, buy_price, buy_qty):
    """
    @params pair: string, 
    @params buy_price: string, will be transformed into float
    @params buy_qty: string, will be transformed into float
    returns true or isinstance dict always
    """
    # Rate limit check
    req = requests.get(url=info_url).json()
    limits = next((item["filters"] for item in req["symbols"] if item["symbol"] == pair), False)
    # Price limits
    # price >= minPrice
    # (price-minPrice) % tickSize == 0
    min_price = float(next((item["minPrice"] for item in limits if item["filterType"] == "PRICE_FILTER"), 0))
    tick_size = float(next((item["tickSize"] for item in limits if item["filterType"] == "PRICE_FILTER"), 0))

    # Qty limits
    # quantity >= minQty
    # (quantity-minQty) % stepSize == 0
    min_qty = float(next((item["minQty"] for item in limits if item["filterType"] == "LOT_SIZE"), 0))
    step_size = float(next((item["stepSize"] for item in limits if item["filterType"] == "LOT_SIZE"), 0))

    # Min notional = price x quantity
    # p x qty > min_notional
    min_pxq = float(next((item["minNotional"] for item in limits if item["filterType"] == "MIN_NOTIONAL"), 0))


    if float(buy_price) <= min_price:
        error_msg = "[BINBOT] Order cannot be carried: price {} Did not pass min price rate limit {}".format(buy_price, min_price)
        object = { "code": -1102, "msg": error_msg }
        return object

    # if (float(buy_price)-min_price) % tick_size != 0:
    #     print("[BINBOT] Order cannot be carried: price {} Did not pass min price rate limit {} - ticksize".format(buy_price, tick_size))
    #     sys.exit(1)

    if float(buy_qty) <= min_qty:
        error_msg = "[BINBOT] Order cannot be carried: quantity {} Did not pass min quantity rate limit {}".format(buy_price, min_price)
        object = { "code": -1101, "msg": error_msg }
        return object

    # if (float(buy_qty)-min_qty) % step_size != 0:
    #     print("[BINBOT] Order cannot be carried: quantity {} Did not pass min quantity rate limit {} - stepsize".format(buy_price, step_size))
    #     sys.exit(1)

    if (float(buy_price) * float(buy_qty)) < min_pxq:
        error_msg = "[BINBOT] Order cannot be carried: price x quantity {} Did not pass min prices x quantity (min notional) rate limit {}".format(buy_price, min_pxq)
        object = { "code": -1100, "msg": error_msg }
        return object

    print("[BINBOT] All Binance rate limits passed!")
    return