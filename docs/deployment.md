# Deployment
1. This project is deployed using Github actions
2. Pipfile.lock is required to do production dependency installation `pipenv install` in Dockerfile
3. One Dockerfile builds 2 apps: api and web
4. Research app is a separate Docker app
## Central market CVD collector

Deploy the schema/API before starting the opt-in `cvd_collector` Compose profile.
Observe real subscription coverage before enabling `VITE_MARKET_CVD_ENABLED` in
the terminal build. See [market CVD operations and protocol](market-cvd.md) for
the exact rollout, retention, ownership, restart and gap semantics.
