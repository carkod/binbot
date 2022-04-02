
from api.deals.schema import DealSchema
from api.tools.enum_definitions import EnumDefinitions
from flask import current_app
from datetime import date

class BotSchemaValidation(Exception):
    pass


class BotSchema:
    """
    Blueprint of the bots collection on MongoDB
    All validation and database fields new or old handled here
    """
    statuses = ["inactive", "active", "completed", "error", "archived"]

    def __init__(self) -> None:
        """
        Set up optional defaults
        """
        self.pair: str = "BNBBTC"
        self.status: str = "inactive"
        self.name: str = "Default bot"
        self.mode: str = "manual"
        self.balance_usage_size: float = 100
        self.base_order_size: str = "0.0001" # Min Binance
        self.balance_to_use: str = "GBP"
        self.base_order_type: str = "limit"
        self.candlestick_interval: str = "15m"
        self.take_profit: float = 3
        self.trailling: str = "false"
        self.trailling_deviation: float = 0.63
        self.trailling_profit: float = 0 # Trailling activation (first take profit hit)
        self.orders: list = [] # Internal
        self.stop_loss: float = 0
        # Deal and orders are internal, should never be updated by outside data
        self.deal: object = DealSchema()
        self.max_so_count: int = 0
        self.safety_orders: object = {}
        self.errors: list[str] = []
        self.total_commission: float = 0
    
    def validate_percentage(self, property, data):
        """Support function for validate_model to reduce repetition"""

        if property in data:
            if not isinstance(data.get(property), (int, float)):
                try:
                    if 0 <= float(data.get(property)) <= 100:
                        setattr(self, property, float(data.get(property)))
                    else:
                        raise BotSchemaValidation(f"{property} must be an integer or float percentage")
                except Exception:
                    raise BotSchemaValidation(f"{property} must be an integer or float percentage")
            setattr(self, property, float(data.get(property)))
            del data[property]
        return data


    def validate_model(self, data):

        try:
            self.pair = data.get("pair")
            check_cannibalism = current_app.db.paper_trading.find_one({"pair": self.pair, "status": "active"})
            if check_cannibalism and not data.get("_id"):
                raise BotSchemaValidation(f"Bot canibalism: there is an active bot trading with this pair")
            else:
                del data["pair"]
        except Exception as e:
            raise BotSchemaValidation(f"pair is required")
        
        if "status" in data:
            if not isinstance(data.get("status"), str) and data.get("status") in self.statuses:
                raise BotSchemaValidation(f"status must be {', '.join(self.statuses)}")
                    
            self.status = data.get("status")
            del data["status"]
        
        if "name" in data:
            if not isinstance(data.get("name"), str):
                raise BotSchemaValidation(f"name must be a string")
            else:
                self.name = data["name"] if data["name"] != "" else f"{data['pair']}-{date.today()}"
                del data["name"]
        
        if "mode" in data:
            if not isinstance(data.get("mode"), str):
                raise BotSchemaValidation(f"mode must be a string")
            self.mode = data.get("mode")
            del data["mode"]
        
        if "balance_usage_size" in data:
            if not isinstance(data.get("balance_usage_size"), (int, float)):
                try:
                    if 0 <= float(data.get("balance_usage_size")) <= 100:
                        self.balance_usage_size = float(data.get("balance_usage_size"))
                    else:
                        raise BotSchemaValidation(f"balance_usage_size must be percentage")
                except Exception:
                    raise BotSchemaValidation(f"balance_usage_size must be percentage")
            self.balance_usage_size = data.get("balance_usage_size")
            del data["balance_usage_size"]
        
        if "base_order_size" in data:
            if not isinstance(data.get("base_order_size"), (int, float)):
                try:
                    if float(data.get("base_order_size")) >= 0.0001:
                        self.base_order_size = data.get("base_order_size")
                    else:
                        raise BotSchemaValidation(
                        f"base_order_size must be a string bigger than 0.0001"
                    )
                except Exception:
                    raise BotSchemaValidation(
                        f"base_order_size must be a string bigger than 0.0001"
                    )
            self.base_order_size = data.get("base_order_size")
            del data["base_order_size"]

        if "balance_to_use" in data:
            if not isinstance(data.get("balance_to_use"), str):
                raise BotSchemaValidation(
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
                raise BotSchemaValidation(
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
                raise BotSchemaValidation(f"trailling must be a Python boolean")
                    
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
                raise BotSchemaValidation(f"errors must be a list")
            else:
                self.errors = data.get("errors")
                del data["errors"]


        if "max_so_count" in data:
            if not isinstance(data.get("max_so_count"), int):
                try:
                     self.max_so_count = int(data.get("max_so_count"))
                except Exception:
                    raise BotSchemaValidation(f"max_so_count must be a Integer")
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
        
        if len(data) > 0:
            for item in data:
                if item != "_id":
                    print(f"Warning: {item} is not in the schema. If this is a new field, please add it to the BotSchema. This field will not be inserted.")

        return self.__dict__

    def update(self, data):
        """Insert logic"""
        validated_data = self.validate_model(data)
        if "_id" in data:
            result = current_app.db.paper_trading.update_one(
                {"_id": data["_id"]}, {"$set": validated_data}, True
            )
        else:
            result = current_app.db.paper_trading.insert_one(validated_data)
        return result

    def get(self):
        bots = current_app.db.paper_trading.find()
        # If mismatch no. fields
        # Make it consistent
        if not bots:
            bots = []
        return bots