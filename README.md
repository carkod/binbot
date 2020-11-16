## Requirements
 
- Docker and docker-compose
- Python 3
- Pipenv. If not installed, run `pip install pipenv`

## Running back-end api

1. Run `pipenv shell` to activate the virtual environment
2. Run vscode debugger to start the Flask application

## Running front-end web app

1. Run `npm run install:clean` and `npm install`
2. Run `npm start`
3. Attach vscode debugger if needed

## Deployment

1. Merge changes to master
2. Checkout master in local
3. Run `deploy.sh`
4. Copy `scp docker-compose.yml <USERNAME>@<SERVER_IP>:/var/www/binbot.carloswu.com`
In production:
5. `docker pull carloswufei/binbot`
6. `docker-compose up -d`

## Test production

1. Run `docker build --tag binbot .`
2. Run `docker-compose up`
