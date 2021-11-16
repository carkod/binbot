# Binance 418 Teapot errors
This error happens actually after rate limits violation. The HTTP codes ocurr in the following order

200 -> 429 -> 418 -> 403 (IP banned)

Source: https://dev.binance.vision/t/how-to-deal-with-http-status-code-at-binance-api/712