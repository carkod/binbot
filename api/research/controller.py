from db import setup_db
from datetime import datetime
from time import sleep
from tools.handle_error import json_response, json_response_error, json_response_message
from pymongo.errors import DuplicateKeyError
from apis import ThreeCommasApi
from tools.round_numbers import round_numbers
from pymongo import ASCENDING
from fastapi.encoders import jsonable_encoder

class Controller:
    """
    Research app settings
    - Get: get single document with settings
    - Set: change single document
    """

    def __init__(self):
        self.db = setup_db()

    def get_blacklist(self):
        """
        Get list of blacklisted symbols
        """
        query_result = self.db.blacklist.find({ "pair": { "$exists": True } }).sort("pair", ASCENDING)
        blacklist = list(query_result)
        return json_response(
            {"message": "Successfully retrieved blacklist", "data": blacklist}
        )

    def create_blacklist_item(self, data):

        try:
            blacklist_item = data.dict()
            blacklist_item["_id"] = data.pair
            self.db.blacklist.insert_one(blacklist_item)
            return json_response(
                {"message": "Successfully updated blacklist"}
            )
        except DuplicateKeyError:
            return json_response({"message": "Pair already exists in blacklist", "error": 1})
        except Exception as error:
            print(error)
            return json_response_error(f"Failed to add pair to black list: {error}")

    def delete_blacklist_item(self, pair):

        blacklist = self.db.blacklist.delete_one({"_id": pair})

        if blacklist.acknowledged:
            resp = json_response({"message": "Successfully deleted item from blacklist", "data": str(pair)})
        else:
            resp = json_response_error("Item does not exist")

        return resp

    def edit_blacklist(self, data):
        if "pair" not in data:
            return json_response({"message": "Missing required field 'pair'.", "error": 1})

        blacklist = self.db.blacklist.update_one(
            {"_id": data["pair"]}, {"$set": data}
        )

        if not blacklist:
            resp = json_response_error("Blacklist item does not exist")

        resp = json_response(
            {"message": "Successfully updated blacklist", "blacklist": blacklist}
        )
        return resp
    
    def store_profitable_signals(self):
        """
        3commas signals that are profitable
        in the past week

        Uses the average of min and max to compute AYP
        """
        print("Storing profitable signals from 3commas.io...")
        consolidated_signals = []
        api = ThreeCommasApi()
        items = api.get_all_marketplace_item()

        for item in items:
            signals = api.get_marketplace_item_signals(item
            ["id"])
            if hasattr(signals, "status"):
                sleep(10)
                signals = api.get_marketplace_item_signals(item
            ["id"])
            portfolio = []
            total_ayp = 0
            previous_ts = ""
            pairs = []
            for signal in signals:
                if signal["exchange"] == "Binance" and signal["signal_type"] == "long" and signal["min"] and signal["max"]:
                    pairs.append(signal["pair"])
                    current_ts = datetime.fromtimestamp(signal["timestamp"]).strftime("%Y-%m-%d")
                    avg_return = float(signal["min"]) + float(signal["max"]) / 2
                    if current_ts == previous_ts:
                        total_ayp += avg_return
                    else:
                        total_ayp += avg_return
                        asset = {
                            "time": current_ts,
                            "estimated_ayp": round_numbers(total_ayp, 4),
                            "pairs": pairs
                        }
                        portfolio.append(asset)
                    
                    previous_ts = datetime.fromtimestamp(signal["timestamp"]).strftime("%Y-%m-%d")

            consolidated_signals.append({
                "id": item["id"],
                "name": item["name"],
                "portfolio": portfolio,
            })

        try:
            self.db.three_commas_signals.delete_many({})    
            self.db.three_commas_signals.insert_many(consolidated_signals)
        except Exception as err:
            print(err)

        print("Successfully stored new 3commas.io signals", consolidated_signals)

    def get_3commas_signals(self):
        """
        Retrieve 3commas.io/marketplace signals
        per week
        """
        query = {}
        signals = list(self.db.three_commas_signals.find(query))

        return json_response({"message": "Successfully retrieved profitable 3commas signals", "data": signals})

    """
    Get pairs that binbot-research signals are subscribed to
    receive cryptodata

    To merge with blacklist
    """
    def get_subscribed_symbols(self):
        query_result = self.db.subscribed_symbols.find({}).sort("pair", ASCENDING)
        all_symbols = list(query_result)
        return json_response(
            {"message": "Successfully retrieved blacklist", "data": all_symbols}
        )

    def delete_all_subscribed_symbols(self):
        query_result = self.db.subscribed_symbols.delete_many({})

        return json_response(
            {"message": "Successfully deleted all symbols", "data": {
                "total": 0
            }}
        )

    def bulk_upsert_all(self, data):
        symbols = jsonable_encoder(data)
        self.db.subscribed_symbols.delete_many({})
        try:
            query_result = self.db.subscribed_symbols.insert_many(
                symbols,
            )
            return json_response(
                {"message": "Successfully created new susbcribed list", "data": {
                    "total": len(query_result.inserted_ids) + 1
                }}
            )
        except Exception as error:
            return json_response_error(f"Failed to update symbol in the subscribed list {error}")

    def edit_subscribed_symbol(self, symbol):
        symbol = jsonable_encoder(symbol)
        try:
            self.db.subscribed_symbols.update_one(
                symbol,
                upsert=True,
            )
            return json_response_message("Successfully update symbol in the subscribed list")
        except Exception as error:
            return json_response_error(f"Failed to update symbol in the subscribed list {error}")