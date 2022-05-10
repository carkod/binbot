import os
import threading

from apscheduler.schedulers.background import BackgroundScheduler

from new_tokens import NewTokens
from telegram_bot import WhaleAlert
from signals import ResearchSignals
import time

if os.getenv("ENV") != "ci":
    scheduler = BackgroundScheduler()
    nt = NewTokens()
    scheduler.add_job(
        func=nt.run,
        timezone="Europe/London",
        trigger="interval",
        hours=6,
    )
    scheduler.start()

    whale_alert = WhaleAlert()
    whale_alert.run_bot()

if __name__ == "__main__":
    rs = ResearchSignals()
    rs_thread = threading.Thread(
        name="rs_thread", target=rs.start_stream
    )
    rs_thread.start()

    try:
        # This is here to simulate application activity (which keeps the main thread alive).
        while True:
            time.sleep(5)
    except (KeyboardInterrupt, SystemExit):
        # Not strictly necessary if daemonic mode is enabled but should be done if possible
        scheduler.shutdown()
