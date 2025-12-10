from typing import List

from pydantic_settings import BaseSettings


class Config(BaseSettings):
    bot_token: str
    admin_ids: str = ""
    payment_provider_token: str = ""
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "product_bot"
    db_user: str = "postgres"
    db_password: str = "postgres"
    log_level: str = "INFO"
    withdrawal_min_amount: float = 100.0
    withdrawal_fee_percent: float = 5.0

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def admin_ids_list(self) -> List[int]:
        if not self.admin_ids:
            return []
        return [int(id_str.strip()) for id_str in self.admin_ids.split(",")]

    class Config:
        env_file = "../.env"
        env_file_encoding = "utf-8"