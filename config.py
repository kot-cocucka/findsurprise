from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    bot_token: str = Field(
        alias="BOT_TOKEN",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def admin_ids(self) -> list[int]:
        return [self.admin_id]


settings = Settings()


def get_settings() -> Settings:
    return settings
