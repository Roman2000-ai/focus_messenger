from pydantic import BaseModel, Field, AliasChoices


class MessageDTO(BaseModel):
    """схема для отправки сообщения через  telethon(telegram api)"""
    username: str = Field(
        
        validation_alias=AliasChoices('username', "contact","peer")
    )
    message: str

class AddContactPayload(BaseModel):
    """схема для добавления контакта для получения данных с помощью telethon(telegram api) для отпавки сообщения"""
    identifier: str

class SendContactDTO(BaseModel):
    """схема для отправки данных контакта на  frontend"""

    telegram_id: int
    username: str| None = None
    first_name: str| None = None
    last_name: str| None = None
    phone: str| None = None

    class Config:
        from_attributes = True