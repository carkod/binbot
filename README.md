## Requirements
 
- MongoDB
- Python 3.7
- Docker
- Conda environment used to setup vscode debugging

## Setup instructions

This project does not run without credentials and API urls, it requires a `.env` file.

## Running project in local development

- Trigger debugger in vscode will `flask run`, it will use .vscode settings.json and launch.json.
- To trigger the web app, `npm start` in the directory


## Running the app in production mode

This project uses docker to containerize resources needed run the project.

1. Run `docker build --tag binbot .` to build an image
2. Run `docker run -it binbot -p 5000:80` to create a container with the image
3. Go to localhost:5000 to view the app as a deployed application
