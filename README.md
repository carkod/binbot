## Requirements
 
- MongoDB
<<<<<<< HEAD
- Python 3 (defaults to Python 3.7, but you can change this in the Pipfile before setup)
- Docker
- Filled `.env` file
=======
- Python 3.7
- Docker
- Conda environment used to setup vscode debugging
>>>>>>> origin/master

## Running API

<<<<<<< HEAD
1. Build image `docker build --tag binbot .`
3. Run container `docker run -p 5000:5000 -ti binbot`

## Auth tokens

There is front-end example with React in place within the `/web` directory. It demonstrates making a few API calls (User Add and User Login).

A successful login request will return two tokens: `AccessToken` and `RefreshToken`. These should be saved to localStorage and used to set the `AccessToken` and `RefreshToken` request headers for all protected routes (e.g. `GET /user/`).

You can refresh the `AccessToken` when it returns as expired by submitting a request to `GET /user/auth/`.
=======
This project does not run without credentials and API urls, it requires a `.env` file.

## Running project in local development

- Trigger debugger in vscode will `flask run`, it will use .vscode settings.json and launch.json.
- To trigger the web app, `npm start` in the directory


## Running the app in production mode

This project uses docker to containerize resources needed run the project.

1. Run `docker build --tag binbot .` to build an image
2. Run `docker run -it binbot -p 5000:80` to create a container with the image
3. Go to localhost:5000 to view the app as a deployed application
>>>>>>> origin/master
