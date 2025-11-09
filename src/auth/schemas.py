from pydantic import BaseModel

class TelegramAuthPayload(BaseModel):
    """схема для получения данных при авторизации через telegram-widget"""         
    id: int                                   
    first_name: str|None = None           
    last_name: str|None = None            
    username: str|None = None             
    photo_url: str|None = None             
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
    """схема для    получения телефона при авторизации на telegram api"""
    phone: str        
    

class PhoneCodeDTO(BaseModel):
    """схема для получения кода при авторизации на telegram api"""
    flow_id: str      
    code: str         

class PhonePwdDTO(BaseModel):
    """схема для получения пароля при авторизации на telegram api(2fa)"""
    flow_id: str      
    password: str       



class QRstatusDTO(BaseModel):
    """ схема для получения проверки статуса при авторизации на telegram api(qr)"""
    flow_id: str



class TwofaDTO(BaseModel):
    """схема для получения пароля при авторизации на telegram api(2fa)"""

    password: str
    flow_id: str

class Flow_idDTO(BaseModel):
    """ схема для получения проверки статуса при авторизации на telegram api(qr)"""
    flow_id: str