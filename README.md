[![Test Production](https://github.com/carkod/binbot/actions/workflows/pr.yml/badge.svg)](https://github.com/carkod/binbot/actions/workflows/pr.yml)

## Architecture
![image](https://github.com/carkod/binbot/assets/14939793/fbfde06b-1dba-4183-9c4e-26e68a48fa10)


## Requirements

- Docker and docker-compose
- Python 3
- Pipenv. If not installed, run `pip install pipenv`

## Running back-end api

1. Run `pipenv shell` to activate the virtual environment
2. Comment out api service and `docker-compose up -d`
3. Run vscode debugger to start the FastAPI application

New packages or installing from scratch:

- `pipenv lock --clear`
- `pipenv install`

## Running front-end web app

1. Run `npm run install:clean`
2. Run `npm start`
3. Attach vscode debugger if needed

## Deployment

1. Merge changes to master
2. Test on local:

- `cd web && yarn build` This is to avoid docker javascript leap out of memory error
- Build and test docker container `docker build --tag binbot . && docker run -ti -p 8000:80 binbot`
- Publish to docker hub `docker build --tag binbot . && docker tag binbot carloswufei/binbot:latest && docker push carloswufei/binbot`

3. Wait for check to pass. Github action will publish to Docker Hub

If docker-compose doesn't exist: 3. Copy `scp docker-compose.yml <USERNAME>@<SERVER_IP>:/var/www/binbot.carloswu.com`
4. Modify details to match production needs

or `docker build --tag binbot . && docker tag binbot carloswufei/binbot:latest && docker push carloswufei/binbot`

In production: 
5. `docker-compose pull && docker-compose up -d` 
6. If `.env.prod` is modified, scp to remote server and replace `.env` in production with new `.env.prod`

## Test production

1. Run `docker build --tag binbot .`
2. Run `docker-compose up`

If issues are encountered downloading prod DB to local

1. Dump database: `docker exec binbot_db sh -c 'mongodump --authenticationDatabase admin -u <user> -p <password> --db binbot --archive' > db.dump`
2. On local, restore `docker exec -i binbot_db sh -c 'mongorestore --archive -u <MONGO_AUTH_USERNAME> -p <MONGO_AUTH_PASSWORD> --authenticationDatabase <MONGO_AUTH_DATABASE> ' < db.dump`


## Detailed documentation

https://carkod.github.io/binbot/
