# Autotrade

## Restrictions
- Autotrade doesn't work with fiat currencies at the moment. It assumes GBP as main conversion fiat and uses it for hedging, but apart from that, Binance also allows trading with currencies such as Australian dollar (AUD), American dollar (USD), CNY (Chinese yuan) etc... which are skipped in the algo (research/__init__.py, skipped_fiat_currencies) on top of the blacklist cryptocurrencies, which are more specific cases.
- Autotrade checks for global settings from research_controller
- Autotrade checks for availability of balance
- Autotrade checks for existent active bots, to avoid creating the same bot