## Requirements
 
- MongoDB
- Python 3 (defaults to Python 3.7, but you can change this in the Pipfile before setup)
- Docker
- Filled `.env` file

## Running API

1. Build image `docker build --tag binbot .`
3. Run container `docker run -p 5000:5000 -ti binbot`

## Auth tokens

There is front-end example with React in place within the `/web` directory. It demonstrates making a few API calls (User Add and User Login).

A successful login request will return two tokens: `AccessToken` and `RefreshToken`. These should be saved to localStorage and used to set the `AccessToken` and `RefreshToken` request headers for all protected routes (e.g. `GET /user/`).

You can refresh the `AccessToken` when it returns as expired by submitting a request to `GET /user/auth/`.

## Error codes

### Bot `-11XX`
`-1100` `Binance min_notional violation`