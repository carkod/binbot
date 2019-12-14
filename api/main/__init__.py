from flask import Flask, request
from flask_cors import CORS
from pymongo import MongoClient
from main.tools import JsonResp
from jose import jwt
import os
from flask_socketio import send, SocketIO

# Import Routes
from main.user.routes import user_blueprint
from main.account.routes import account_blueprint
from main.bots.routes import bot_blueprint
from main.deals.routes import deal_blueprint
from main.orders.routes import order_blueprint
from main.userDataStream.routes import userDataStream_blueprint

def create_app():

  # Flask Config
  app = Flask(__name__)
  app.config.from_pyfile("config/config.cfg")
  cors = CORS(app, resources={r"/*": { "origins": app.config["FRONTEND_DOMAIN"] }})
  socketio = SocketIO(app)
  socketio.run(app, debug=True)
  # Misc Config
  os.environ["TZ"] = app.config["TIMEZONE"]

  mongo = MongoClient(app.config["MONGO_HOSTNAME"], app.config["MONGO_PORT"])
  mongo[app.config["MONGO_AUTH_DATABASE"]].authenticate(app.config["MONGO_AUTH_USERNAME"], app.config["MONGO_AUTH_PASSWORD"])
  app.db = mongo[app.config["MONGO_APP_DATABASE"]]

  # Register Blueprints
  app.register_blueprint(user_blueprint, url_prefix="/user")
  app.register_blueprint(account_blueprint, url_prefix="/account")
  app.register_blueprint(bot_blueprint, url_prefix="/bot")
  app.register_blueprint(deal_blueprint, url_prefix="/deal")
  app.register_blueprint(order_blueprint, url_prefix="/order")
  app.register_blueprint(userDataStream_blueprint, url_prefix="/user-data-stream")

  # Index Route
  @app.route("/")
  def index():
    return JsonResp({ "status": "Online" }, 200)
  
  @socketio.on('message')
  def handle_message(message):
    send(message)

  return app