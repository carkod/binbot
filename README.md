[![Test Production](https://github.com/carkod/binbot/actions/workflows/pr.yml/badge.svg)](https://github.com/carkod/binbot/actions/workflows/pr.yml)

<img width="2067" height="1885" alt="Binbot architecture-2025-10-26-144727" src="https://github.com/user-attachments/assets/cd3b76a4-0653-421c-b8e0-24685b7d6dd8" />

# Development instructions

## Requirements

- Docker and docker-compose
- Python 3.11
- UV. If not installed, run `pip install uv`

## Run services

`docker compose up -d`

This should create and set up the Postgres database.

> Open source note:
> you'll need data for the entire project to work,
> which I do not provide

## Running back-end api

1. Run `uv sync` to activate the virtual environment
2. Comment out api service and `docker-compose up -d`
3. Run vscode debugger to start the FastAPI application

### Back-end api developer tooling

- For tests: `make test` or use `.vscode` folder config
- Install new dependencies with: `uv add <package-name>`
- Formatting with `make format`
- Upgrade pybinbot `make upgrade-pybinbot`

## Running front-end web app

1. Run `npm run install:clean`
2. Run `npm start`
3. Attach vscode debugger if needed

### Front-end tooling

- `npm run build` to test a production bundle locally
- `npm run test` to run unit tests
- `npm run format` to prettier format files, although this should be set up with the vscode prettier plugin

## Production deployment

Trigger manually the Github action `prod-deploy.yml`.
Each repo has its own, so cronjob, streaming and api is deployed using this Github action, binquant and the other repos should have their own independent deployment pipeline.

## API DB updates using Alembic

Use the `Makefile` to generate alembic migration scripts

### To remove a previously created migration

```
alembic stamp 113eb73ebba8
```

where 113eb73ebba8 is the supposed last "good" migration that you want to revert to.

## Manual Deployment

1. Merge changes to master
2. Test on local:

- `cd terminal && npm start`
- Build and test docker container `docker build --tag binbot . && docker run -ti -p 8000:80 binbot`
- Publish to docker hub `docker build --tag binbot . && docker tag binbot carloswufei/binbot:latest && docker push carloswufei/binbot`

3. Wait for check to pass. Github action will publish to Docker Hub

### Additional steps

If docker-compose doesn't exist: 3. Copy `scp docker-compose.yml <USERNAME>@<SERVER_IP>:/var/www/binbot.carloswu.com` 4. Modify details to match production needs

or `docker build --tag binbot . && docker tag binbot carloswufei/binbot:latest && docker push carloswufei/binbot`

In production: 5. `docker compose up --pull always -d` 6. If `.env.prod` is modified, scp to remote server and replace `.env` in production with new `.env.prod`

## Detailed documentation

https://carkod.github.io/binbot/
