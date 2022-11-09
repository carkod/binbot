from datetime import datetime
from time import sleep
from api.app import create_app
from api.research.test_autotrade_schema import TestAutotradeSchema
from api.tools.handle_error import jsonResp, jsonResp_error_message, jsonResp_message
from flask import current_app, request
from pymongo.errors import DuplicateKeyError
from api.research.controller_schema import ControllerSchema
from api.apis import ThreeCommasApi
from api.tools.round_numbers import round_numbers
from pymongo import ASCENDING

class Controller:
    """
    Research app settings
    - Get: get single document with settings
    - Set: change single document
    """

    def __init__(self):
        self.default_blacklist = {"_id": "", "pair": "", "reason": ""}  # pair

    def get_blacklist(self) -> jsonResp:
        """
        Get list of blacklisted symbols
        """
        query_result = current_app.db.blacklist.find({ "pair": { "$exists": True } }).sort("pair", ASCENDING)
        blacklist = list(query_result)
        return jsonResp(
            {"message": "Successfully retrieved blacklist", "data": blacklist}
        )

    def create_blacklist_item(self):
        data = request.json
        if "pair" not in data:
            return jsonResp({"message": "Missing required field 'pair'.", "error": 1})

        self.default_blacklist.update(data)
        self.default_blacklist["_id"] = data["pair"]
        try:
            blacklist = current_app.db.blacklist.insert_one(self.default_blacklist)
        except DuplicateKeyError:
            return jsonResp({"message": "Pair already exists in blacklist", "error": 1})

        if blacklist:
            resp = jsonResp(
                {"message": "Successfully updated blacklist", "data": str(blacklist)}
            )
        else:
            resp = jsonResp({"message": "Failed to update blacklist", "error": 1})

        return resp

    def delete_blacklist_item(self):
        pair = request.view_args["pair"]

        blacklist = current_app.db.blacklist.delete_one({"_id": pair})

        if blacklist.acknowledged:
            resp = jsonResp({"message": "Successfully updated blacklist"})
        else:
            resp = jsonResp({"message": "Item does not exist", "error": 1})

        return resp

    def edit_blacklist(self):
        data = request.json
        if "pair" not in data:
            return jsonResp({"message": "Missing required field 'pair'.", "error": 1})

        self.default_blacklist.update(data)
        blacklist = current_app.db.blacklist.update_one(
            {"_id": data["pair"]}, {"$set": self.default_blacklist}
        )

        if not blacklist:
            current_app.db.blacklist.insert(self.default_blacklist)

        resp = jsonResp(
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
        app = create_app()
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
            app.db.three_commas_signals.delete_many({})    
            app.db.three_commas_signals.insert_many(consolidated_signals)
        except Exception as err:
            print(err)

        print("Successfully stored new 3commas.io signals", consolidated_signals)

    def get_3commas_signals(self):
        """
        Retrieve 3commas.io/marketplace signals
        per week
        """
        query = {}
        signals = list(current_app.db.three_commas_signals.find(query))

        return jsonResp({"message": "Successfully retrieved profitable 3commas signals", "data": signals})


