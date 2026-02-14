# Exchange Integrations

After multi-tenant work was compeleted. Binbot now supports connection to multiple exchanges. This is all wired up in the DealGateway interface.

## Storage

1. New exchanges have to be created as an Enum, in the Pybinbot module.
2. Stored in the autotrade_settings table

## Deal Gateway

Deal gateway (DealGateway class) is a common inferface for all crypto exchange connection. It is what ties up Binbot system with any other exchange. If you look at api/deals/gateway.py, it must contain a number of methods

- open_deal
- deactivation
- save
- deal_exit_orchestration

This file is a Facade software pattern, where you pretty much just list the mandatory methods. It is a way to keep consistency across exchanges, it does not enforce logic. Underlying logic is withi those functions that it returns.

Notice I haven't included `update_logs`, because bot logs should work the same across exchanges, it simply records the important actions in the bot (customized by the developer).


## Process of integration with new exchanges

To integrate new exchanges, we create an API layer in the api/exchange_apis. Folder naming can be up to the functionality of this layer, because some exchange provide good Pypi libraries to handle connections to the API so it can be greatly simplified.

All the exchange-specific logic will be written in those files, which eventually need to bubble up to the Deal Gateway interface, which must have those 4 mandatory methods to interact with the bots. The logic of when to choose one Exchange or the other will lie on the DealGateway.__init__ and that will hook up those mandatory methods.

Deals are the bridge between bots and exchanges.