from pydantic import BaseSettings


class KonaSettings(BaseSettings):
    KONA_PROJECT_NAME: str = "kona"

    DEFAULT_KEY_VALUE_STORE_TYPE: str = "rocksdb"
    KONA_LOG_ENABLE_LOGGER: bool = False

    class Config:
        case_sensitive = True


settings = KonaSettings()
