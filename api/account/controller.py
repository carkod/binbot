from account.account import Account
from database.mongodb.db import Database
from tools.handle_error import json_response
from account.schemas import BalanceSchema
from bson.objectid import ObjectId
from datetime import datetime


class AssetsController(Database, Account):
    """
    Database operations abstraction for assets/balances
    """

    def __init__(self):
        super().__init__()

    def create_balance_series(self, total_balance, total_estimated_fiat: float):
        """
        Abstraction to reduce complexity
        updates balances DB collection
        """
        balance_schema = BalanceSchema(
            balances=total_balance, estimated_total_usdc=total_estimated_fiat
        )
        response = self._db.balances.insert_one(
            {
                "balances": balance_schema.balances,
                "estimated_total_usdc": balance_schema.estimated_total_usdc,
            }
        )
        return response

    def query_balance_series(self, start_date: int, end_date: int):
        """
        Abstraction to reduce complexity
        fetches balances DB collection
        """
        params: dict = {}

        if start_date:
            start_date = start_date * 1000
            try:
                float(start_date)
            except ValueError:
                resp = json_response(
                    {"message": "start_date must be a timestamp float", "data": []}
                )
                return resp

            obj_start_date = datetime.fromtimestamp(int(float(start_date) / 1000))
            gte_tp_id = ObjectId.from_datetime(obj_start_date)
            try:
                params["_id"]["$gte"] = gte_tp_id
            except KeyError:
                params["_id"] = {"$gte": gte_tp_id}

        if end_date:
            end_date = end_date * 1000
            try:
                float(end_date)
            except ValueError as e:
                resp = json_response(
                    {"message": f"end_date must be a timestamp float: {e}", "data": []}
                )
                return resp

            obj_end_date = datetime.fromtimestamp(int(float(end_date) / 1000))
            lte_tp_id = ObjectId.from_datetime(obj_end_date)
            params["_id"]["$lte"] = lte_tp_id

        query = self._db.balances.find(
            params,
            projection={
                "time": {
                    "$dateToString": {"format": "%Y-%m-%d", "date": {"$toDate": "$_id"}}
                },
                "balances": 1,
                "estimated_total_usdt": 1,
                "estimated_total_usdc": 1,
                "_id": 0,
            },
        ).sort([("_id", -1)])
        balance_series = list(query)
        return balance_series
