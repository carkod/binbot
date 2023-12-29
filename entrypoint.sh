#!/bin/bash

exec python3 -u market_updates.py &
exec python3 -u order_updates.py
