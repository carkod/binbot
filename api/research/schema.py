class ControllerModel:
    def __init__(self, candlestick_interval="1h", autotrade=0, trailling_profit=2.4, stop_loss=3, trailling="true", trailling_deviation="3", update_required=False, balance_to_use="BNB", balance_size_to_use=100, max_request=950, system_logs=[], errors=[]):
        return {
            "candlestick_interval": candlestick_interval,
            "autotrade": autotrade,
            "trailling_profit": trailling_profit,
            "stop_loss": stop_loss,
            "trailling": trailling,
            "trailling_deviation": trailling_deviation,
            "update_required": update_required,  # Changed made, need to update websockets
            "balance_to_use": balance_to_use,
            "balance_size_to_use": balance_size_to_use,  # %
            "max_request": max_request,
            "system_logs": system_logs,
            "errors": errors,
        }
      
    def run_validation(self):
      pass
      #   db.runCommand( {
#     collMod: "contacts",
#     validator: { $jsonSchema: {
#         bsonType: "object",
#         required: [ "phone", "name" ],
#         properties: {
#           phone: {
#               bsonType: "string",
#               description: "must be a string and is required"
#           },
#           name: {
#               bsonType: "string",
#               description: "must be a string and is required"
#           }
#         }
#     } },
#     validationLevel: "moderate"
#   } )
