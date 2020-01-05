## Requirements
 
- MongoDB
- Python 3 (defaults to Python 3.7, but you can change this in the Pipfile before setup)

## Setup instructions

1. Clone this repo to your local web server
2. `cd` into the directory within the terminal
3. Run `./setup` to setup pipenv and configure the Flask app

Here's a quick video of the setup process (no audio): [flask-mongo-api-boilerplate-setup.mp4](https://img.lukepeters.me/flask-mongo-api-boilerplate-setup.mp4)

## Running the app

1. Create a virtual environment with conda
2. Run `./run` to start the Flask application

## Further configuration

You can configure the app manually by editing the `.env` file.

## Auth tokens

There is front-end example with React in place within the `/web` directory. It demonstrates making a few API calls (User Add and User Login).

A successful login request will return two tokens: `AccessToken` and `RefreshToken`. These should be saved to localStorage and used to set the `AccessToken` and `RefreshToken` request headers for all protected routes (e.g. `GET /user/`).

You can refresh the `AccessToken` when it returns as expired by submitting a request to `GET /user/auth/`.