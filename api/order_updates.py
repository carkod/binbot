import asyncio
from pybinbot import configure_logging
from streaming.kucoin_order_ws import KucoinOrderWS
from os import getenv
from dotenv import load_dotenv

load_dotenv()


async def main():
    # initialization data
    configure_logging(force=True)
    ws = KucoinOrderWS(
        api_key=getenv("KUCOIN_KEY", ""),
        api_secret=getenv("KUCOIN_SECRET", ""),
        api_passphrase=getenv("KUCOIN_PASSPHRASE", ""),
    )
    await ws.subscribe_orders()
    await ws.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
