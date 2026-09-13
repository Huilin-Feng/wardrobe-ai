from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings loaded from the .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str = ""
    weather_api_key: str = ""
    database_url: str = "sqlite:///./wardrobe.db"
    upload_dir: str = "./uploads"


# Single shared instance — import this everywhere instead of creating new ones
settings = Settings()