from time import sleep
from api.app import create_app
from api.research.test_autotrade_schema import TestAutotradeSchema
from api.tools.handle_error import jsonResp, jsonResp_error_message, jsonResp_message
from flask import current_app, request
from pymongo.errors import DuplicateKeyError
from api.research.controller_schema import ControllerSchema
from api.apis import ThreeCommasApi

class Controller:
    """
    Research app settings
    - Get: get single document with settings
    - Set: change single document
    """

    def __init__(self):
        self.default_blacklist = {"_id": "", "pair": "", "reason": ""}  # pair

    def get_settings(self):
        settings = ControllerSchema().get()

        if settings:
            resp = jsonResp(
                {"message": "Successfully retrieved settings", "data": settings}
            )
        else:
            resp = jsonResp_error_message(
                "Database error ocurred. Could not retrieve settings."
            )
        return resp

    def edit_settings(self):
        data = request.get_json()
        controller_schema = ControllerSchema()
        try:
            controller_schema.update(data)
            resp = jsonResp_message("Successfully updated settings")
        except TypeError as e:
            resp = jsonResp_error_message(f"Data validation error: {e}")
        return resp

    def get_blacklist(self) -> jsonResp:
        """
        Get list of blacklisted symbols
        """
        blacklist = list(current_app.db.blacklist.find())
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
    
    def get_test_autotrade_settings(self):
        settings = TestAutotradeSchema().get()

        if settings:
            resp = jsonResp(
                {"message": "Successfully retrieved settings", "data": settings}
            )
        else:
            resp = jsonResp_error_message(
                "Database error ocurred. Could not retrieve settings."
            )
        return resp

    def edit_test_autotrade_settings(self):
        data = request.get_json()
        controller_schema = TestAutotradeSchema()
        try:
            controller_schema.update(data)
            resp = jsonResp_message("Successfully updated settings")
        except TypeError as e:
            resp = jsonResp_error_message(f"Data validation error: {e}")
        return resp

    def store_profitable_signals(self):
        """
        3commas signals that are profitable
        in the past week
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
            for signal in signals:
                print(signal["pair"])
                if signal["exchange"] == "Binance" and signal["signal_type"] == "long":
                    portfolio.append(signal)

            consolidated_signals.append({
                "id": item["id"],
                "name": item["name"],
                "portfolio": portfolio
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


