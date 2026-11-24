"""Host CVD shards, refresh contracts and checkpoint within streaming.main."""

import asyncio
from functools import partial
import logging
import time

from streaming.cvd.contracts import load_contracts
from streaming.cvd.flow import Flow, handle_message
from streaming.cvd.storage import owner_connection, persist, restore
from streaming.shared.kucoin_futures import stream_executions

log = logging.getLogger("cvd")
SHARD_SIZE = 100  # Operational choice; Classic Futures currently has no topic cap.


async def run(stop: asyncio.Event) -> None:
    # Never allow SQLAlchemy to reconnect this owner connection after failure.
    async with owner_connection() as connection:
        flow = Flow(await asyncio.to_thread(load_contracts), time.time_ns())
        await asyncio.to_thread(restore, connection, flow)
        tasks: list[asyncio.Task] = []
        next_refresh = time.time() + 900
        pending_contracts = None
        graceful = False
        try:
            while not stop.is_set():
                now = time.time()
                flow.tick(now)
                if now >= next_refresh:
                    try:
                        pending_contracts = await asyncio.to_thread(load_contracts)
                        next_refresh = now + 900
                    except Exception:
                        log.exception("contract refresh failed")
                        next_refresh = now + 60
                if (
                    pending_contracts is not None
                    and pending_contracts != flow.contracts
                    and int(now) % 60 < 10
                ):
                    for task in tasks:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                    tasks = []
                    flow.disconnect(list(flow.contracts), now)
                    flow.contracts = pending_contracts
                    # Membership changes take effect at the NEXT UTC minute.
                    next_minute = int(now) // 60 * 60 + 60
                    log.info(
                        "universe refreshed effective_minute=%s symbols=%s",
                        next_minute,
                        len(flow.contracts),
                    )
                if not tasks and flow.contracts:
                    symbols = sorted(flow.contracts)
                    tasks = [
                        asyncio.create_task(
                            stream_executions(
                                symbols[i : i + SHARD_SIZE],
                                stop,
                                partial(handle_message, flow),
                                flow.disconnect,
                            )
                        )
                        for i in range(0, len(symbols), SHARD_SIZE)
                    ]
                    log.info(
                        "connections=%s subscriptions=%s", len(tasks), len(symbols)
                    )
                for task in tasks:
                    if task.done():
                        task.result()
                        raise RuntimeError("CVD shard exited unexpectedly")
                snapshot = flow.snapshot(now)
                try:
                    await asyncio.to_thread(persist, connection, snapshot, now)
                except Exception:
                    log.exception(
                        "flush failed; stopping owner, restart will retain saved totals and mark uncertainty"
                    )
                    raise
                flow.prune(now)
                log.info(
                    "checkpoint=%s expected=%s acknowledged=%s covered=%s last_trade_ns=%s trades=%s dedup_entries=%s rejected=%s",
                    int(now),
                    len(flow.contracts),
                    len(flow.acknowledged),
                    snapshot[1][-1]["covered_symbols"] if snapshot[1] else 0,
                    flow.last_trade_ns,
                    flow.trades,
                    flow.seen_count,
                    flow.rejected,
                )
                try:
                    await asyncio.wait_for(stop.wait(), 10)
                except TimeoutError:
                    pass
            graceful = True
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            # Graceful shutdown preserves arrivals since last checkpoint, and marks
            # the unfinished connection interval partial just like an abrupt stop.
            flow.disconnect(list(flow.contracts), time.time() - 30)
            if graceful and not connection.invalidated:
                await asyncio.to_thread(
                    persist, connection, flow.snapshot(time.time()), time.time()
                )
