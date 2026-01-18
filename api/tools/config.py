from dotenv import load_dotenv
import os

load_dotenv()


class ConfigurationError(Exception):
    """
    Raised when required environment variable is missing
    """

    pass


class Config:
    """
    Singleton that validates and provides access to environment variables

    Configuration module for loading environment variables.
    Loads .env file and makes variables available via os.getenv()

    Load environment variables from .env file
    Searches for .env in current directory and parent directories automatically

    Won't override existing environment variables (useful for production)
    """

    def __init__(self):
        self._env = os.getenv("ENV", "")
        self._ci_mode = self._env.lower() == "ci"
        self._validate_required_vars()

    def _get_required(self, key: str) -> str:
        """Get required environment variable or raise exception"""
        value = os.getenv(key)
        if value is None or value == "":
            if self._ci_mode:
                return ""
            raise ConfigurationError(
                f"Required environment variable '{key}' is not set"
            )
        return value

    def _get_optional(self, key: str, default: str = "") -> str:
        """Get optional environment variable with fallback default"""
        value = os.getenv(key)
        if value is None or value == "":
            return default
        return value

    def _validate_required_vars(self):
        """Validate that all required environment variables are present"""
        if self._ci_mode:
            return

        required_vars = [
            "PYTHONUNBUFFERED",
            "DEBUG",
            "LOG_LEVEL",
            "TZ",
            "SECRET_KEY",
            "ENV",
            "BACKEND_DIRECTORY",
            "BACKEND_DOMAIN",
            "FRONTEND_DOMAIN",
            "MONGO_HOSTNAME",
            "MONGO_AUTH_DATABASE",
            "MONGO_AUTH_USERNAME",
            "MONGO_AUTH_PASSWORD",
            "MONGO_APP_DATABASE",
            "MONGO_KAFKA_DATABASE",
            "KAFKA_HOST",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "POSTGRES_DB",
            "POSTGRES_HOSTNAME",
            "USER",
            "PASSWORD",
            "EMAIL",
            "BINANCE_KEY",
            "BINANCE_SECRET",
            "KUCOIN_KEY",
            "KUCOIN_SECRET",
            "KUCOIN_PASSPHRASE",
            "TELEGRAM_BOT_KEY",
            "TELEGRAM_USER_ID",
        ]

        missing = [var for var in required_vars if not os.getenv(var)]
        if missing and not self._ci_mode:
            raise ConfigurationError(
                f"Missing required environment variables: {', '.join(missing)}"
            )

    @property
    def log_level(self) -> str:
        return self._get_required("LOG_LEVEL")

    @property
    def timezone(self) -> str:
        return self._get_required("TZ")

    @property
    def secret_key(self) -> str:
        return self._get_required("SECRET_KEY")

    @property
    def env(self) -> str:
        return self._get_required("ENV")

    @property
    def backend_directory(self) -> str:
        return self._get_required("BACKEND_DIRECTORY")

    @property
    def backend_domain(self) -> str:
        return self._get_required("BACKEND_DOMAIN")

    @property
    def frontend_domain(self) -> str:
        return self._get_required("FRONTEND_DOMAIN")

    # MongoDB settings
    @property
    def mongo_hostname(self) -> str:
        return self._get_required("MONGO_HOSTNAME")

    @property
    def mongo_port(self) -> int:
        return int(self._get_optional("MONGO_PORT", "27018"))

    @property
    def mongo_auth_database(self) -> str:
        return self._get_required("MONGO_AUTH_DATABASE")

    @property
    def mongo_auth_username(self) -> str:
        return self._get_required("MONGO_AUTH_USERNAME")

    @property
    def mongo_auth_password(self) -> str:
        return self._get_required("MONGO_AUTH_PASSWORD")

    @property
    def mongo_app_database(self) -> str:
        return self._get_required("MONGO_APP_DATABASE")

    @property
    def mongo_kafka_database(self) -> str:
        return self._get_required("MONGO_KAFKA_DATABASE")

    # Kafka settings
    @property
    def kafka_port(self) -> int:
        return int(self._get_optional("KAFKA_PORT", "29092"))

    @property
    def kafka_host(self) -> str:
        return self._get_required("KAFKA_HOST")

    # PostgreSQL settings
    @property
    def postgres_user(self) -> str:
        return self._get_required("POSTGRES_USER")

    @property
    def postgres_password(self) -> str:
        return self._get_required("POSTGRES_PASSWORD")

    @property
    def postgres_db(self) -> str:
        return self._get_required("POSTGRES_DB")

    @property
    def postgres_hostname(self) -> str:
        return self._get_required("POSTGRES_HOSTNAME")

    # User settings
    @property
    def user(self) -> str:
        return self._get_required("USER")

    @property
    def password(self) -> str:
        return self._get_required("PASSWORD")

    @property
    def email(self) -> str:
        return self._get_required("EMAIL")

    # Binance settings
    @property
    def binance_key(self) -> str:
        return self._get_required("BINANCE_KEY")

    @property
    def binance_secret(self) -> str:
        return self._get_required("BINANCE_SECRET")

    # KuCoin settings
    @property
    def kucoin_key(self) -> str:
        return self._get_required("KUCOIN_KEY")

    @property
    def kucoin_secret(self) -> str:
        return self._get_required("KUCOIN_SECRET")

    @property
    def kucoin_passphrase(self) -> str:
        return self._get_required("KUCOIN_PASSPHRASE")

    # Telegram settings
    @property
    def telegram_bot_key(self) -> str:
        return self._get_required("TELEGRAM_BOT_KEY")

    @property
    def telegram_user_id(self) -> str:
        return self._get_required("TELEGRAM_USER_ID")
