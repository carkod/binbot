# Paper trading

/api/paper-trading is a copy of /bot created to test /research/ algorithms. It works similarly using the autotrade settings, but it has a few less features compared to the real thing. It does not trade with real funds.

## List of active bots

Using a `self.app.db.bots.distinct("pair", {"status": "active"})` as an endpoint, somehow causes a Topology error in MongoDB. I suppose the data gets corrupted as websockets update data while at the same time deleting bots.