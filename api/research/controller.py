from db import setup_db
from datetime import datetime
from time import sleep
from tools.handle_error import json_response, json_response_error
from pymongo.errors import DuplicateKeyError
from apis import ThreeCommasApi
from tools.round_numbers import round_numbers
from pymongo import ASCENDING

class Controller:
    """
    Research app settings
    - Get: get single document with settings
    - Set: change single document
    """

    def __init__(self):
        self.default_blacklist = {"_id": "", "pair": "", "reason": ""}  # pair
        self.db = setup_db()

    def get_blacklist(self) -> json_response:
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
            data.dict()
            data["_id"] = data["pair"]
            self.db.blacklist.insert_one(self.default_blacklist)
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

        self.default_blacklist.update(data)
        blacklist = self.db.blacklist.update_one(
            {"_id": data["pair"]}, {"$set": self.default_blacklist}
        )

        if not blacklist:
            self.db.blacklist.insert(self.default_blacklist)

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


