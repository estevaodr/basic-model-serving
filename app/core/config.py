from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    torch_num_threads: int = 2
    max_upload_bytes: int = 1048576
    url_timeout: float = 5.0
    log_level: str = "INFO"


settings = Settings()
