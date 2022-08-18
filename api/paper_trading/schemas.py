
from api.bots.schemas import SafetyOrderSchema
from api.deals.schema import DealSchema
from api.tools.enum_definitions import EnumDefinitions
from flask import current_app
from datetime import date
from api.bots.models import BotSchema
class BotSchemaValidation(Exception):
    pass


class PaperTradingBotSchema(BotSchema):
    """
    Blueprint of the bots collection on MongoDB
    All validation and database fields new or old handled here
    """

    def __init__(self):
        return super().__init__()
    
    def validate_test_bot(self, data):

        # If there is cannibalism, fail the trade
        # only for testing bots
        try:
            self.pair = data.get("pair")
            check_cannibalism = current_app.db.paper_trading.find_one({"pair": self.pair, "status": "active"})
            if check_cannibalism and not data.get("_id"):
                raise BotSchemaValidation(f"Bot canibalism: there is an active bot trading with this pair")
            else:
                del data["pair"]
        except Exception as e:
            raise BotSchemaValidation(e)
        
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
        
        if "balance_size_to_use" in data:
            if not isinstance(data.get("balance_size_to_use"), (int, float)):
                try:
                    if 0 <= float(data.get("balance_size_to_use")) <= 100:
                        self.balance_size_to_use = float(data.get("balance_size_to_use"))
                    else:
                        raise BotSchemaValidation(f"balance_size_to_use must be percentage")
                except Exception:
                    raise BotSchemaValidation(f"balance_size_to_use must be percentage")
            self.balance_size_to_use = data.get("balance_size_to_use")
            del data["balance_size_to_use"]
        
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
            so_schema = SafetyOrderSchema()
            self.safety_orders = so_schema.dump(data.get("safety_orders"))

            del data["safety_orders"]
        
        if "deal" in data:
            deal_schema = DealSchema()
            self.deal = deal_schema.dump(data.get("deal"))
            del data["deal"]
        
        if "orders" in data:
            self.orders = data.get("orders")
            del data["orders"]
        
        if "cooldown" in data:
            try:
                float(data["cooldown"])
            except Exception:
                raise BotSchemaValidation(
                    f"cooldown must be a number integer or decimal"
                )
            self.cooldown = data.get("cooldown")
            del data["cooldown"]
        
        if len(data) > 0:
            for item in data:
                if item != "_id":
                    print(f"Warning: {item} is not in the schema. If this is a new field, please add it to the BotSchema. This field will not be inserted.")

        return self.__dict__

    def update_test_bots(self, data):
        """Insert logic"""
        validated_data = self.validate_test_bot(data)
        if "_id" in data:
            result = current_app.db.paper_trading.update_one(
                {"_id": data["_id"]}, {"$set": validated_data}, True
            )
        else:
            result = current_app.db.paper_trading.insert_one(validated_data)
        return result

    def get_test_bots(self, sort=[], params={}):
        bots = current_app.db.paper_trading.find(params).sort(sort)
        return list(bots)
