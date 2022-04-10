from api.tools.enum_definitions import EnumDefinitions
from flask import current_app
from copy import deepcopy

class NewFieldError(Exception):
    pass


class TestAutotradeSchema:
    """
    Centralizes the data structure
    - to protect the MongoDB from inconsistencies setting old and new fields
    - validation of fields and types

    """

    def __init__(self) -> None:
        id = "test_autotrade_settings"
        settings = current_app.db.research_controller.find_one({"_id": id})
        try:
            self.candlestick_interval = settings["candlestick_interval"]
            self.test_autotrade = settings["test_autotrade"]
            self.trailling = settings["trailling"]
            self.trailling_deviation = settings["trailling_deviation"]
            self.trailling_profit = settings["trailling_profit"]
            self.stop_loss = settings["stop_loss"]
            self.take_profit = settings["take_profit"]
            self.balance_to_use = settings["balance_to_use"]
            self.balance_size_to_use = settings["balance_size_to_use"]
        except Exception:
            self.candlestick_interval = "15m"
            self.test_autotrade = 0
            self.trailling = "true"
            self.trailling_deviation = 3
            self.trailling_profit = 2.4
            self.stop_loss = 3
            self.take_profit = 2.4
            self.balance_to_use = "GBP"
            self.balance_size_to_use = 100

    def validate_model(self, data):
        if "_id" in data:
            del data["_id"]

        if "candlestick_interval" in data:
            if (
                not isinstance(data.get("candlestick_interval"), str)
                and data.get("candlestick_interval")
                not in EnumDefinitions.chart_intervals
            ):
                raise TypeError(
                    f"candlestick_interval must be a String value among these {str(EnumDefinitions.chart_intervals)}"
                )
            elif data.get("candlestick_interval") is not None:
                self.candlestick_interval = data.get("candlestick_interval")

            del data["candlestick_interval"]

        if "test_autotrade" in data:
            if not isinstance(data.get("test_autotrade"), int) and data.get(
                "test_autotrade"
            ) not in [0, 1]:
                try:
                    self.test_autotrade = int(data.get("test_autotrade"))
                except Exception:
                    raise TypeError(f"test_autotrade must be a Integer 0 or 1")
            elif data.get("test_autotrade") is not None:
                self.test_autotrade = data.get("test_autotrade")

            del data["test_autotrade"]

        if "trailling" in data:
            if not isinstance(data.get("trailling"), int) and data.get(
                "trailling"
            ) not in ["true", "false"]:
                raise TypeError(f"trailling must be a String true or false")
            elif not data.get("trailling") is not None:
                self.trailling = data.get("trailling")

            del data["trailling"]

        if "take_profit" in data:
            if not isinstance(data.get("take_profit"), (int, float)):
                try:
                    self.take_profit = float(data.get("take_profit"))
                except Exception:
                    raise TypeError(f"take_profit must be a Real number")
            elif not data.get("take_profit") is not None:
                self.take_profit = data.get("take_profit")

            del data["take_profit"]

        if "stop_loss" in data:
            if not isinstance(data.get("stop_loss"), (int, float)):
                try:
                    self.stop_loss = float(data.get("stop_loss"))
                except Exception:
                    raise TypeError(f"stop_loss must be a Real number")
            elif not data.get("stop_loss") is not None:
                self.stop_loss = data.get("stop_loss")

            del data["stop_loss"]

        if "trailling_deviation" in data:
            if not isinstance(data.get("trailling_deviation"), (int, float)):
                try:
                    self.trailling_deviation = float(data.get("trailling_deviation"))
                except Exception:
                    raise TypeError(f"trailling_deviation must be a Real number")
            elif not data.get("trailling_deviation") is not None:
                self.trailling_deviation = data.get("trailling_deviation")

            del data["trailling_deviation"]

        if "trailling_profit" in data:
            if not isinstance(data.get("trailling_profit"), (int, float)):
                try:
                    self.trailling_profit = float(data.get("trailling_profit"))
                except Exception:
                    raise TypeError(f"trailling_profit must be a String true or false")
            elif not data.get("trailling_profit") is not None:
                self.trailling_profit = data.get("trailling_profit")

            del data["trailling_profit"]

        if "balance_size_to_use" in data:
            if not isinstance(data.get("balance_size_to_use"), int):
                try:
                    if 1 <= float(data.get("balance_size_to_use")) <= 100:
                        self.balance_size_to_use = float(
                            data.get("balance_size_to_use")
                        )
                except Exception:
                    raise TypeError(
                        f"balance_size_to_use must be a positive integer between 0 and 100"
                    )
            elif not data.get("balance_size_to_use") is not None:
                self.balance_size_to_use = data.get("balance_size_to_use")

            del data["balance_size_to_use"]

        if "balance_to_use" in data:
            self.balance_to_use = data.get("balance_to_use")
            del data["balance_to_use"]

        if len(data) > 0:
            for item in data:
                raise TypeError(
                    f"{item} was not found. If this is a new field, please add it to the ControllerSchema"
                )

        return self.__dict__

    def update(self, data):
        """Insert logic"""
        validated_data = self.validate_model(data)
        current_app.db.research_controller.update_one(
            {"_id": self.id}, {"$set": validated_data}, True
        )
        pass

    def get(self):
        settings = current_app.db.research_controller.find_one({"_id": self.id})
        return settings
