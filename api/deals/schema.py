from time import time


class SafetyOrdersErrorValidation(Exception):
    pass


def DealSchema():
    """
    To become a proper class with validations in the future
    """
    return {
        "last_order_id": 0,
        "buy_timestamp": 0,
        "buy_price": "",
        "buy_total_qty": "",
        "current_price": "",
        "take_profit_price": "",
        "so_prices": [],
        "sell_timestamp": 0,
        "sell_price": "",
        "sell_qty": "",
        "post_closure_current_price": "",
    }


class SafetyOrdersSchema:
    def __init__(self, name="so_1", order_id="", buy_price="0", mode = "manual", max_so_count = 0, locked_in_funds=0) -> None:
        """
        Set up optional defaults
        """
        self.name = name # should be so_<index>
        self.pair: str = ""
        self.order_id: str = order_id
        self.created_at: float = time() * 1000
        self.updated_at: float = time() * 1000
        self.buy_price: str = buy_price
        self.buy_timestamp: str = ""
        self.mode: str = mode
        self.max_so_count: int = max_so_count
        self.locked_in_funds: float = locked_in_funds # Amount of funds locked in so that it can't be used by other bots
        self.errors: list[str] = []
        self.total_commission: float = 0
        return [self.__dict__]
    
    def validate_percentage(self, property, data):
        """Support function for validate_model to reduce repetition"""

        if property in data:
            if not isinstance(data.get(property), (int, float)):
                try:
                    if 0 <= float(data.get(property)) <= 100:
                        setattr(self, property, float(data.get(property)))
                    else:
                        raise SafetyOrdersErrorValidation(f"{property} must be an integer or float percentage")
                except Exception:
                    raise SafetyOrdersErrorValidation(f"{property} must be an integer or float percentage")
            setattr(self, property, float(data.get(property)))
            del data[property]
        return data


    def validate_model(self, data):

        if "_id" in data:
            del data["_id"]

        if "name" in data:
            if not isinstance(data.get("name"), str):
                raise SafetyOrdersErrorValidation(f"name must be a string")
            else:
                self.name = data["name"] if data["name"] != "" else f"{data['pair']}-{date.today()}"
                del data["name"]
        
        if "updated_at" in data:
            self.updated_at = time() * 1000
            del data["updated_at"]
        
        if "mode" in data:
            if not isinstance(data.get("mode"), str):
                raise SafetyOrdersErrorValidation(f"mode must be a string")
            self.mode = data.get("mode")
            del data["mode"]
        
        if "balance_usage_size" in data:
            if not isinstance(data.get("balance_usage_size"), (int, float)):
                try:
                    if 0 <= float(data.get("balance_usage_size")) <= 100:
                        self.balance_usage_size = float(data.get("balance_usage_size"))
                    else:
                        raise SafetyOrdersErrorValidation(f"balance_usage_size must be percentage")
                except Exception:
                    raise SafetyOrdersErrorValidation(f"balance_usage_size must be percentage")
            self.balance_usage_size = data.get("balance_usage_size")
            del data["balance_usage_size"]
        
        if "base_order_size" in data:
            if not isinstance(data.get("base_order_size"), (int, float)):
                try:
                    if float(data.get("base_order_size")) >= 0.0001:
                        self.base_order_size = data.get("base_order_size")
                    else:
                        raise SafetyOrdersErrorValidation(
                        f"base_order_size must be a string bigger than 0.0001"
                    )
                except Exception:
                    raise SafetyOrdersErrorValidation(
                        f"base_order_size must be a string bigger than 0.0001"
                    )
            self.base_order_size = data.get("base_order_size")
            del data["base_order_size"]

        if "balance_to_use" in data:
            if not isinstance(data.get("balance_to_use"), str):
                raise SafetyOrdersErrorValidation(
                        f"balance_to_use must be a string asset name"
                    )
            self.balance_to_use = data.get("balance_to_use")
            del data["balance_to_use"]


        if "candlestick_interval" in data:
            if (
                not isinstance(data.get("candlestick_interval"), str)
                and data.get("candlestick_interval")
                not in EnumDefinitions.chart_intervals
            ):
                raise SafetyOrdersErrorValidation(
                    f"candlestick_interval must be a String value among these {str(EnumDefinitions.chart_intervals)}"
                )
            elif not data.get("candlestick_interval"):
                self.candlestick_interval = data.get("candlestick_interval")

            del data["candlestick_interval"]


        
        if "take_profit" in data:
            data = self.validate_percentage("take_profit", data)

        if "stop_loss" in data:
            data = self.validate_percentage("stop_loss", data)

        if "trailling_deviation" in data:
            data = self.validate_percentage("trailling_deviation", data)

        if "trailling_profit" in data:
            data = self.validate_percentage("trailling_profit", data)

        if "trailling" in data:
            if not isinstance(data.get("trailling"), str):
                raise SafetyOrdersErrorValidation(f"trailling must be a Python boolean")
                    
            if (
                data.get("trailling") == "true"
                or data.get("trailling") == "True"
                or data.get("trailling") == "false"
                or data.get("trailling") == "False"
            ):
                self.trailling = data.get("trailling")
                del data["trailling"]

        if "errors" in data:
            if not isinstance(data.get("errors"), list):
                raise SafetyOrdersErrorValidation(f"errors must be a list")
            else:
                self.errors = data.get("errors")
                del data["errors"]


        if "max_so_count" in data:
            if not isinstance(data.get("max_so_count"), int):
                try:
                     self.max_so_count = int(data.get("max_so_count"))
                except Exception:
                    raise SafetyOrdersErrorValidation(f"max_so_count must be a Integer")
            else:
                self.max_so_count = data.get("max_so_count")

            del data["max_so_count"]
        
        if "safety_orders" in data:
            self.safety_orders = data.get("safety_orders")

            del data["safety_orders"]
        
        if "deal" in data:
            self.deal = data.get("deal")
            del data["deal"]
        
        if "orders" in data:
            self.orders = data.get("orders")
            del data["orders"]

        if "cooldown" in data:
            try:
                float(data["cooldown"])
            except Exception:
                raise SafetyOrdersErrorValidation(
                    f"cooldown must be a number integer or decimal"
                )
            self.cooldown = data.get("cooldown")
            del data["cooldown"]
        
        if len(data) > 0:
            for item in data:
                if item != "_id":
                    print(f"Warning: {item} is not in the schema. If this is a new field, please add it to the BotSchema. This field will not be inserted.")

        return self.__dict__

    def update(self, data):
        """Insert logic"""
        id = None
        if "_id" in data:
            id = data["_id"]
        validated_data = self.validate_model(data)
        if id:
            # Delete internal attributes created by bot
            # Only when updating existing
            del validated_data["deal"]
            del validated_data["orders"]
            del validated_data["created_at"]
            result = current_app.db.bots.update_one(
                {"_id": ObjectId(id)}, {"$set": validated_data}
            )
        else:
            validated_data["created_at"] = time() * 1000
            result = current_app.db.bots.insert_one(validated_data)
        return result
