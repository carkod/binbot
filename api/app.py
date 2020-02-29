from main import create_app
import logging
import os

app = create_app()

if __name__ == "__main__":
    app.run(host=os.environ["FLASK_DOMAIN"], port=os.environ["FLASK_PORT"])
else:
    logging.basicConfig(
        filename=os.environ["FLASK_DIRECTORY"] + "trace.log", level=logging.DEBUG
    )
