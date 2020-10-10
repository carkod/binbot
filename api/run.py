from main import create_app
import os
app = create_app()

if __name__ == "__main__":
    app.run(host=os.environ["FLASK_DOMAIN"], port=os.environ["FLASK_PORT"])
