from time import time
import uuid

from api.tools.enum_definitions import EnumDefinitions


class BotSchemaValidation(Exception):
    pass

class SafetyOrderModel:
    def __init__(
        self,
        buy_price,
        safety_order_size,
        name="so_1",
        order_id="",
        buy_timestamp=0,
        errors=[],
        total_comission=0,
    ):
        self.name: str = name  # should be so_<index>
        self.order_id: str = order_id
        self.created_at: float = time() * 1000
        self.updated_at: float = time() * 1000
        self.buy_price: float = buy_price
        self.buy_timestamp: float = buy_timestamp
        self.safety_order_size: float = safety_order_size
        self.errors: list[str] = errors
        self.total_commission: float = total_comission

class BotModel:
    """
    Blueprint of the bots collection on MongoDB
    All validation and database fields new or old handled here
    """
    def __init__(
        self,
        pair: str,
        base_order_size: str,
        id = None,
        created_at = time() * 1000,
        updated_at = time() * 1000,
        take_profit: float = 3,
        status: str = EnumDefinitions.statuses[0],
        name: str = "Default bot",
        mode: str = "manual",
        balance_usage_size: float = 0,
        balance_to_use: str = "USDT",
        candlestick_interval: str = "15m",
        trailling: str = "false",
        trailling_deviation: float = 0.63,
        trailling_profit: float = 0, # Trailling activation (first take profit hit),
        orders: list = [], # Internal
        stop_loss: float = 0,
        # Deal and orders are internal, should never be updated by outside data,
        deal: object = {},
        errors: list[str] = [],
        total_commission: float = 0,
        cooldown: float = 0,
        # Safety orders,
        locked_so_funds: float = 0,
        safety_orders = []
    ) -> None:
        self._id = id or uuid.uuid4().hex
        self.pair = pair
        self.status = status
        self.name = name
        self.created_at = created_at
        self.updated_at = updated_at
        self.mode = mode
        self.balance_usage_size = balance_usage_size
        self.base_order_size = base_order_size
        self.balance_to_use = balance_to_use
        self.candlestick_interval = candlestick_interval
        self.take_profit = take_profit
        self.trailling = trailling
        self.trailling_deviation = trailling_deviation
        self.trailling_profit = trailling_profit
        self.orders = orders
        self.stop_loss = stop_loss
        # Deal and orders are internal, should never be updated by outside data
        self.deal = deal
        self.errors = errors
        self.total_commission = total_commission
        self.cooldown = cooldown
        # Safety orders
        self.locked_so_funds = locked_so_funds
        self.safety_orders = safety_orders

    
#     def validate_percentage(self, property, data):
#         """Support function for validate_model to reduce repetition"""

#         if property in data:
#             if not isinstance(data.get(property), (int, float)):
#                 try:
#                     if 0 <= float(data.get(property)) <= 100:
#                         setattr(self, property, float(data.get(property)))
#                     else:
#                         raise BotSchemaValidation(f"{property} must be an integer or float percentage")
#                 except Exception:
#                     raise BotSchemaValidation(f"{property} must be an integer or float percentage")
#             setattr(self, property, float(data.get(property)))
#             del data[property]
#         return data


#     def validate_model(self, data):

#         if "_id" in data:
#             del data["_id"]

#         try:
#             self.pair = data.get("pair")
#         except Exception as e:
#             raise BotSchemaValidation(f"{e.args[0]}")
#         del data["pair"]
        
#         if "status" in data:
#             if not isinstance(data.get("status"), str) and data.get("status") in self.statuses:
#                 raise BotSchemaValidation(f"status must be {', '.join(self.statuses)}")

#             self.status = data.get("status")
#             del data["status"]
        
#         if "name" in data:
#             if not isinstance(data.get("name"), str):
#                 raise BotSchemaValidation(f"name must be a string")
#             else:
#                 self.name = data["name"] if data["name"] != "" else f"{data['pair']}-{date.today()}"
#                 del data["name"]
        
#         if "updated_at" in data:
#             self.updated_at = time() * 1000
#             del data["updated_at"]
        
#         if "mode" in data:
#             if not isinstance(data.get("mode"), str):
#                 raise BotSchemaValidation(f"mode must be a string")
#             self.mode = data.get("mode")
#             del data["mode"]
        
#         if "balance_usage_size" in data:
#             if not isinstance(data.get("balance_usage_size"), (int, float)):
#                 try:
#                     if 0 <= float(data.get("balance_usage_size")) <= 100:
#                         self.balance_usage_size = float(data.get("balance_usage_size"))
#                     else:
#                         raise BotSchemaValidation(f"balance_usage_size must be percentage")
#                 except Exception:
#                     raise BotSchemaValidation(f"balance_usage_size must be percentage")
#             self.balance_usage_size = data.get("balance_usage_size")
#             del data["balance_usage_size"]
        
#         if "base_order_size" in data:
#             if not isinstance(data.get("base_order_size"), (int, float)):
#                 try:
#                     if float(data.get("base_order_size")) >= 0.0001:
#                         self.base_order_size = data.get("base_order_size")
#                     else:
#                         raise BotSchemaValidation(
#                         f"base_order_size must be a string bigger than 0.0001"
#                     )
#                 except Exception:
#                     raise BotSchemaValidation(
#                         f"base_order_size must be a string bigger than 0.0001"
#                     )
#             self.base_order_size = data.get("base_order_size")
#             del data["base_order_size"]

#         if "balance_to_use" in data:
#             if not isinstance(data.get("balance_to_use"), str):
#                 raise BotSchemaValidation(
#                         f"balance_to_use must be a string asset name"
#                     )
#             self.balance_to_use = data.get("balance_to_use")
#             del data["balance_to_use"]


#         if "candlestick_interval" in data:
#             if (
#                 not isinstance(data.get("candlestick_interval"), str)
#                 and data.get("candlestick_interval")
#                 not in EnumDefinitions.chart_intervals
#             ):
#                 raise BotSchemaValidation(
#                     f"candlestick_interval must be a String value among these {str(EnumDefinitions.chart_intervals)}"
#                 )
#             elif not data.get("candlestick_interval"):
#                 self.candlestick_interval = data.get("candlestick_interval")

#             del data["candlestick_interval"]


        
#         if "take_profit" in data:
#             data = self.validate_percentage("take_profit", data)

#         if "stop_loss" in data:
#             data = self.validate_percentage("stop_loss", data)

#         if "trailling_deviation" in data:
#             data = self.validate_percentage("trailling_deviation", data)

#         if "trailling_profit" in data:
#             data = self.validate_percentage("trailling_profit", data)

#         if "trailling" in data:
#             if not isinstance(data.get("trailling"), str):
#                 raise BotSchemaValidation(f"trailling must be a Python boolean")
                    
#             if (
#                 data.get("trailling") == "true"
#                 or data.get("trailling") == "True"
#                 or data.get("trailling") == "false"
#                 or data.get("trailling") == "False"
#             ):
#                 self.trailling = data.get("trailling")
#                 del data["trailling"]

#         if "errors" in data:
#             if not isinstance(data.get("errors"), list):
#                 raise BotSchemaValidation(f"errors must be a list")
#             else:
#                 self.errors = data.get("errors")
#                 del data["errors"]


#         if "max_so_count" in data:
#             if not isinstance(data.get("max_so_count"), int):
#                 try:
#                      self.max_so_count = int(data.get("max_so_count"))
#                 except Exception:
#                     raise BotSchemaValidation(f"max_so_count must be a Integer")
#             else:
#                 self.max_so_count = data.get("max_so_count")

#             del data["max_so_count"]
        
#         # if "safety_orders" in data and data.get("safety_orders") and isinstance(data.get("safety_orders"), list):
#         #     so_schema = SafetyOrderSchema()
#         #     try:
#         #         so_list = []
#         #         for so in data.get("safety_orders"):
#         #             so_model = SafetyOrderModel(buy_price=so["buy_price"], safety_order_size=so["safety_order_size"], name=so["name"], buy_timestamp=so["buy_timestamp"])
#         #             so_list.append(so_schema.load(so_model))

#         #         self.safety_orders = so_list
#         #     except Exception as error:
#         #         BotSchemaValidation(f"Safety order error: {error}")
#         #     del data["safety_orders"]

#         if "deal" in data:
#             self.deal = data.get("deal")
#             del data["deal"]
        
#         if "orders" in data:
#             self.orders = data.get("orders")
#             del data["orders"]

#         if "cooldown" in data:
#             try:
#                 float(data["cooldown"])
#             except Exception:
#                 raise BotSchemaValidation(
#                     f"cooldown must be a number integer or decimal"
#                 )
#             self.cooldown = data.get("cooldown")
#             del data["cooldown"]
        
#         if len(data) > 0:
#             for item in data:
#                 if item != "_id":
#                     print(f"Warning: {item} is not in the schema. If this is a new field, please add it to the BotSchema. This field will not be inserted.")

#         return self.__dict__
