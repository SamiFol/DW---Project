from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "acme_dwh"

    assets_collection: str = "assets"
    timeseries_collection: str = "time_series"
    sources_collection: str = "data_sources"

    api_title: str = "Acme Ltd — Financial Markets Data Warehouse"
    api_version: str = "0.1.0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
