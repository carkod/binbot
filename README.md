## Running back-end api

1. Run `pipenv shell` to activate the virtual environment
2. Run `./run` to start the Flask application

## Running front-end web app

1. Run `npm run install:clean` and `npm install`
2. Run `npm start`


## Requirements
 
- MongoDB
- Python 3 (defaults to Python 3.7, but you can change this in the Pipfile before setup)

## Setup instructions

1. Clone this repo to your local web server
2. `cd` into the directory within the terminal
3. Run `./setup` to setup pipenv and configure the Flask app

## Auth tokens

There is a very basic front-end example in place within the `/web` directory. It demonstrates making a few API calls (User Add and User Login).

A successful login request will return two tokens: `AccessToken` and `RefreshToken`. These should be saved to localStorage and used to set the `AccessToken` and `RefreshToken` request headers for all protected routes (e.g. `GET /user/`).

You can refresh the `AccessToken` when it returns as expired by submitting a request to `GET /user/auth/`.
