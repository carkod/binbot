from datetime import datetime


class BalanceSchemaValidation(Exception):
    pass

class BalanceSchema:
    """
    Blueprint of the bots collection on MongoDB
    All validation and database fields new or old handled here
    """

    def __init__(self) -> None:
        """
        Set up optional defaults
        """
        self.time: datetime = datetime.utcnow().strftime("%Y-%m-%d")
        self.balances: object = {}
        self.estimated_total_usdt: float = 0

    def validate_model(self, data):

        if "_id" in data:
            del data["_id"]

        if "time" in data:
            if not isinstance(data.get("time"), str) and data.get("time"):
                raise BalanceSchemaValidation(f"time must be a datetime object")
                    
            self.time = data.get("time")
            del data["time"]
        
        if "estimated_total_usdt" in data:
            if not isinstance(data.get("estimated_total_usdt"), float) and data.get("estimated_total_usdt"):
                raise BalanceSchemaValidation(f"estimated_total_usdt must be a float")
                    
            self.estimated_total_usdt = data.get("estimated_total_usdt")
            del data["estimated_total_usdt"]
        
        if len(data) > 0:
            for item in data:
                if item != "_id":
                    print(f"Warning: {item} is not in the schema. If this is a new field, please add it to the BotSchema. This field will not be inserted.")

        return self.__dict__