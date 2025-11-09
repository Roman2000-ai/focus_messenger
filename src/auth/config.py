from pydantic_settings import BaseSettings
from pathlib import Path
from typing import ClassVar

class AuthSettings(BaseSettings):
    jwt_secret: str
    jwt_alg: str
    timeout_waiting_qr: int
    timeout_2fa_input: int
    

    tg_allowed_keys: ClassVar[set[str]] = {"id", "first_name", "last_name", "username", "photo_url", "auth_date", "hash"}

    class Config:
        env_file = Path(__file__).parent.parent.parent/'.env'
        extra = "ignore"


auth_settings = AuthSettings()
    