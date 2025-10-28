from typing import Optional
from pydantic import BaseModel, Field, AliasChoices, ConfigDict



class TelegramAuthPayload(BaseModel):           
    id: int                                   
    first_name: Optional[str] = None           
    last_name: Optional[str] = None            
    username: Optional[str] = None             
    photo_url: Optional[str] = None             
    auth_date: int                            
    hash: str               



class TokenOut(BaseModel):
    """
    Ответ при успешной авторизации: наш токен и telegram_id.
    """
    ok: bool            
    telegram_id: int    
    token: str         

class MeOut(BaseModel):
    """
    Ответ защищённого эндпоинта /me (минимальная форма).
    """
    ok: bool  
    user: dict 



class PhoneStartDTO(BaseModel):
    phone: str        
    

class PhoneCodeDTO(BaseModel):
    flow_id: str      
    code: str         

class PhonePwdDTO(BaseModel):
    flow_id: str      
    password: str       


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

class MessageDTO(BaseModel):
    username: str = Field(
        
        validation_alias=AliasChoices('username', "contact","peer")
    )
    message: str

class QRstatusDTO(BaseModel):
    flow_id: str


class AddContactPayload(BaseModel):
    identifier: str



class SendContactDTO(BaseModel):

    telegram_id: int
    username: str| None = None
    first_name: str| None = None
    last_name: str| None = None
    phone: str| None = None

    class Config:
        from_attributes = True

class TwofaDTO(BaseModel):

    password: str
    flow_id: str

class Flow_idDTO(BaseModel):
    flow_id: str