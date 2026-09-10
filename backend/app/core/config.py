from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Hisobchi"
    environment: str = "development"
    database_url: str = "postgresql+asyncpg://hisobchi:hisobchi@localhost:5432/hisobchi"
    bot_token: str = ""
    super_admin_telegram_id: int | None = None
    jwt_secret: str = Field(default="change-me-in-development", min_length=16)
    access_token_minutes: int = 30
    business_timezone: str = "Asia/Tashkent"
    salary_divisor: int = Field(default=30, gt=0)
    owner_profit_percentage: int = Field(default=50, ge=0, le=100)
    partner_profit_percentage: int = Field(default=50, ge=0, le=100)
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def model_post_init(self, __context: object) -> None:
        if self.owner_profit_percentage + self.partner_profit_percentage != 100:
            raise ValueError("Owner and partner profit percentages must total 100")


@lru_cache
def get_settings() -> Settings:
    return Settings()
