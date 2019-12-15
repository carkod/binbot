from main import create_app
import logging
from flask_socketio import send, SocketIO

app = create_app()

if __name__ == "__main__":
  app.run(host=app.config["FLASK_DOMAIN"], port=app.config["FLASK_PORT"])
else:
  logging.basicConfig(filename=app.config["FLASK_DIRECTORY"] + "trace.log", level=logging.DEBUG)