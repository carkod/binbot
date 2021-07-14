from flask import request, current_app as app
from api.tools.jsonresp import jsonResp

class Blacklisted:
    def __init__(self):
        self.defaults = {
            "symbol": "",
            "reason": ""
        }

    def save_blacklisted(self):
        data = request.json()
        self.defaults.update(data)
        item = app.db.blacklist.save(self.defaults, {"$currentDate": {"createdAt": "true"}})
        if item:
            resp = jsonResp(
                {"message": "Successfully created new bot", "item": str(item)}, 200
            )
        else:
            resp = jsonResp({"message": "Failed to create new bot"}, 400)

        return resp

    def get_blacklisted(self):
        item = app.db.blacklist.get(self.defaults)
        if item:
            resp = jsonResp(
                {"data": str(item)}, 200
            )
        else:
            resp = jsonResp({"message": "Failed to get blacklisted cryptos"}, 200)

        return resp
