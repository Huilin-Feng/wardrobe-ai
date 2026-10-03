from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings loaded from the .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    weather_api_key: str = ""
    database_url: str = "sqlite:///./wardrobe.db"
    upload_dir: str = "./uploads"
    # "local" keeps photos on disk (development, tests, CI); "s3" moves them to a private bucket.
    storage_backend: str = "local"
    s3_bucket: str = ""
    aws_region: str = "us-east-2"
    presigned_url_ttl: int = 300
    cors_origins: list[str] = ["http://localhost:5173"]


# Single shared instance — import this everywhere instead of creating new ones
settings = Settings()