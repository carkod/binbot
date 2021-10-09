from api.deals.models import Deal
from api.tools.handle_error import bot_errors, jsonResp, jsonResp_message
from bson.objectid import ObjectId
from flask import request, current_app


class Controller:
    """
    Research app settings
    - Get: get single document with settings
    - Set: change single document
    """

    def __init__(self):
        # Data model
        self.defaults = {
            "_id": "settings",
            "candlestick_interval": "1h",
            "autotrade": 0,
        }


    def get_settings(self):
        settings = current_app.db.reserch_controller.find_one({"_id": "settings"})
        if settings:
            resp = jsonResp({"message": "Successfully retrieved settings", "data": settings})
        else:
            resp = jsonResp({"message": "Failed to retrieve settings"})
        return resp

    def edit_settings(self):
        data = request.json
        self.defaults.update(data)
        settings = current_app.db.reserch_controller.find_one_and_update({"_id": "settings"}, {"$set": self.defaults})

        if not settings:
            current_app.db.reserch_controller.insert(self.defaults)
        
        resp = jsonResp({"message": "Successfully updated settings", "settings": settings})
        return resp
    

    def get_blacklist(self):
        blacklist = current_app.db.reserch_controller.find_one({"_id": "blacklist"})
        if blacklist:
            resp = jsonResp({"message": "Successfully retrieved blacklist", "data": blacklist})
        else:
            resp = jsonResp({"message": "Failed to retrieve blacklist"})
        return resp

    def edit_blacklist(self):
        data = request.json
        self.defaults.update(data)
        blacklist = current_app.db.reserch_controller.find_one_and_update({"_id": "blacklist"}, {"$set": self.defaults})

        if not blacklist:
            current_app.db.reserch_controller.insert(self.defaults)
        
        resp = jsonResp({"message": "Successfully updated blacklist", "blacklist": blacklist})
        return resp
