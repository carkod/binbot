---
layout: default
title: Third party APIs
---

# APIs `/api/apis.py`

This file contains third party API endpoints used by the project. At the time of writing, only URLs are added, as DRY patterns emerge, it should be easy to refactor code and centralize them in this file.

## BinanceApi

This class contains all Binance API endpoints used by the project, only those necessary are progressively included. Reasons why a library is not used intead:
- **Stability**. These endpoints are heavily relied upon. Open source libraries come and go, a library such as python-binance could easily at some point stop being maintained, or contain too much unnecessary overhead.
- **Flexibility**. Changes in a third party library that can break things, add not needed features, not solving issues that are critical for this project to work, will cause instability in this project. Having our own small library not only shrinks library size to a minimum but also allows easily remove or add features as required.

There is a promising lightweight library [Binance connector](https://github.com/binance/binance-connector-python) which is apparently maintained by Binance themselves, so it does not rely on community support. But it still has some limitations in terms of support for features, issues