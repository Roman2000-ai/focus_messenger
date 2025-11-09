from pydantic_settings import  BaseSettings
from pathlib import Path




class TelegramSettings(BaseSettings):
    telegram_bot_token: str
    telegram_username_bot: str
    api_id: str
    api_hash: str
 
    class Config:
        env_file = Path(__file__).parent.parent.parent/'.env'
        extra = "ignore"


telegram_settings  = TelegramSettings()