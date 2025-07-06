from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent / ".env")
    )

    pipenv_venv_in_project: int = 1
    pythonunbuffered: int = 0
    debug: bool = True
    log_level: str = "ERROR"
    timezone: str = "Europe/London"
    secret_key: str = "dev_key"
    env: str = "development"
    flask_directory: str = "/api/"
    flask_domain: str = "http://localhost:8008"
    frontend_domain: str = "http://localhost:3000"
    http_https: str = "http://"
    access_token_expire_minutes: int = 525600
    mongo_hostname: str = "localhost"
    mongo_port: int = 27018
    mongo_auth_database: str
    mongo_auth_username: str
    mongo_auth_password: str
    mongo_app_database: str = "binbot"
    mongo_kafka_database: str = "kafka"
    kafka_port: int = 9092
    kafka_host: str = "localhost"
    pyarrow_ignore_timezone: int = 1
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_hostname: str
    user: str
    password: str
    email: str
    binance_key: str
    binance_secret: str
    btc_wallet: str
    telegram_bot_key: str
    telegram_user_id: int = 1068200613
    grafana_token: str
