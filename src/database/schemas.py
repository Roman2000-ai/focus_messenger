from pydantic import BaseModel, ConfigDict, Field, AliasChoices


class UserDB(BaseModel):
    model_config = ConfigDict(extra='ignore')
    telegram_id: int = Field(
        validation_alias=AliasChoices('id', "telegram_id")
    )
    phone: int|str|None = None
    username: str| None = None
    first_name: str| None = None
    last_name: str| None = None
    photo_url: str| None = None
    auth_date: int|None = None