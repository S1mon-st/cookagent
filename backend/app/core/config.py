from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore", populate_by_name=True)

    app_name: str = "灶边 AI 私厨管家"
    app_env: str = Field(default="development", alias="APP_ENV")
    dashscope_api_key: SecretStr | None = Field(default=None, alias="DASHSCOPE_API_KEY")
    model_base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        alias="MODEL_BASE_URL",
    )
    model_name: str = Field(default="qwen3.7-plus", alias="MODEL_NAME")
    tavily_api_key: SecretStr | None = Field(default=None, alias="TAVILY_API_KEY")
    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")
    max_image_mb: int = Field(default=10, alias="MAX_IMAGE_MB", ge=1, le=20)
    recipe_count: int = Field(default=4, alias="RECIPE_COUNT", ge=3, le=8)

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def model_ready(self) -> bool:
        return bool(self.dashscope_api_key and self.dashscope_api_key.get_secret_value())

    @property
    def tavily_ready(self) -> bool:
        return bool(self.tavily_api_key and self.tavily_api_key.get_secret_value())


@lru_cache
def get_settings() -> Settings:
    return Settings()

