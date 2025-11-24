from pydantic import Field
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    APP_NAME: str = "Controller Status Predict"
    APP_VERSION: str = "1.0"
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DEBUG: bool = True

    ALLOWED_ORIGINS: List[str] = ["*"]

    DEFAULT_THRESHOLDS: List[float] = Field(
        default=[0.1, 0.3, 0.5, 0.7, 0.9],
        min_items=5,
        max_items=5,
        env="DEFAULT_THRESHOLDS",
        description="Default thresholds for predict"
    )
    # [mixed, heart, video]
    DEFAULT_MODELS: List[int] = Field(
        default=[1, 1, 1],
        min_items=3,
        max_items=3,
        env="DEFAULT_MODELS",
        description="Default models for predict"
    )

    DEFAULT_PREDICT_TIME_LENGTH: str = Field(
        default="10min",
        env="DEFAULT_PREDICT_TIME_LENGTH",
        description="Default predict time length"
    )

    DATABASE_URL: str = Field(
        default="mysql+aiomysql://root:root123@localhost:3306/heartDb?charset=utf8mb4",
        env="DATABASE_URL"
    )
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        env="REDIS_URL"
    )
    REDIS_TTL: int = Field(
        default=3600,
        env="REDIS_TTL"
    )
    REDIS_PASSWORD: str = Field(
        default="letmein123",
        env="REDIS_PASSWORD"
    )
    DATABASE_ECHO: bool = Field(
        default=False,
        env="DATABASE_ECHO"
    )

    LOG_LEVEL: str = Field(
        default="INFO",
        env="LOG_LEVEL"
    )
    LOG_FILE: str = Field(
        default="logs/app.log",
        env="LOG_FILE"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
