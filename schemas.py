from typing import Optional
from pydantic import BaseModel, Field, AliasChoices, ConfigDict



class TelegramAuthPayload(BaseModel):           # создаём модель данных с помощью Pydantic
    id: int                                     # уникальный идентификатор пользователя Telegram
    first_name: Optional[str] = None            # имя (может отсутствовать)
    last_name: Optional[str] = None             # фамилия (может отсутствовать)
    username: Optional[str] = None              # username (может отсутствовать)
    photo_url: Optional[str] = None             # ссылка на аватар (может отсутствовать)
    auth_date: int                              # unix-временная метка, когда данные сформированы Telegram
    hash: str               



class TokenOut(BaseModel):
    """
    Ответ при успешной авторизации: наш токен и telegram_id.
    """
    ok: bool            # флаг успеха
    telegram_id: int    # идентификатор пользователя Telegram
    token: str          # выданный приложением JWT

class MeOut(BaseModel):
    """
    Ответ защищённого эндпоинта /me (минимальная форма).
    """
    ok: bool  # флаг успеха
    user: dict  # полезная нагрузка токена (claims)



class PhoneStartDTO(BaseModel):
    phone: str        # телефон в международном формате: "+3816...."
    #web_user_id: str  # id пользователя твоего сайта, чтобы к нему привязать сессию

class PhoneCodeDTO(BaseModel):
    flow_id: str      # id флоу, который вернулся из /auth/phone/start
    code: str         # код, пришедший в Telegram/SMS

class PhonePwdDTO(BaseModel):
    flow_id: str      # тот же id флоу
    password: str     # парол   


class UserDB(BaseModel):
    model_config = ConfigDict(extra='ignore')
    telegram_id: int = Field(
        validation_alias=AliasChoices('id', "telegram_id")
    )
    username: str| None = None
    first_name: str| None = None
    last_name: str| None = None
    photo_url: str| None = None
    auth_date: int|None = None

class MessageDTO(BaseModel):
    user: str
    message: str