# Deployment
1. This project is deployed using Github actions
2. Pipfile.lock is required to do production dependency installation `pipenv install` in Dockerfile
3. One Dockerfile builds 2 apps: api and web
4. Research app is a separate Docker app