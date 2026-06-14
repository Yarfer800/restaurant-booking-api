from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    app_name: str = "Restaurant Booking API"
    environment: str = "development"
    echo_sql: bool = False

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/restaurant_booking"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


config = Config()
