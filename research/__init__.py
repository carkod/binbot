import os
import threading
import time
import atexit
import logging
import sys

from apscheduler.schedulers.background import BackgroundScheduler

from algorithms.new_tokens import NewTokens
from algorithms.whale_alert_signals import WhaleAlertSignals
from qfl_signals import QFL_signals
from signals import ResearchSignals

root = logging.getLogger()
root.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)

if os.getenv("ENV") != "ci":
    scheduler = BackgroundScheduler()
    nt = NewTokens()
    scheduler.add_job(
        func=nt.run,
        timezone="Europe/London",
        trigger="interval",
        hours=6,
    )
    wa = WhaleAlertSignals()
    scheduler.add_job(
        func=wa.run_bot,
        timezone="Europe/London",
        trigger="interval",
        hours=6,
    )

    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())

if __name__ == "__main__":
    rs = ResearchSignals()
    rs_thread = threading.Thread(
        name="rs_thread", target=rs.start_stream
    )
    rs_thread.start()
    qfl = QFL_signals()
    qfl_thread = threading.Thread(
        name="qfl_thread", target=qfl.start_stream
    )
    qfl_thread.start()
    global stop_threads
    stop_threads = False
    try:
        # This is here to simulate application activity (which keeps the main thread alive).
        while True:
            time.sleep(5)
            if stop_threads:
                break
    except (KeyboardInterrupt, SystemExit):
        # Not strictly necessary if daemonic mode is enabled but should be done if possible
        scheduler.shutdown()
