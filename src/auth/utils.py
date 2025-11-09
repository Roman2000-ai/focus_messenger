import time
import jwt
from src.auth.config import auth_settings
from src.auth.constants import  EXP_ACCESS_TOKEN, EXP_REFRESH_TOKEN
from src.telegram.config import telegram_settings 
import hashlib
import hmac

TELEGRAM_BOT_TOKEN = telegram_settings.telegram_bot_token
JWT_SECRET = auth_settings.jwt_secret
JWT_ALG = auth_settings.jwt_alg

def create_access_jwt(user_id: int) -> str:
    """
    Создаёт наш собственный JWT для сессии приложения.
    Кладём sub=telegram_id, плюс стандартные метки iat/exp.
    """
   
    payload = {}  
    payload["sub"] = str(user_id)  
    payload["iat"] = int(time.time())  
    payload["exp"] = int(time.time()) + EXP_ACCESS_TOKEN 

    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)  
    return token  

def create_refresh_jwt(subject: str) -> str:
    """
    Создаёт долгоживущий refresh-JWT.
    """
    now = int(time.time())                              
    payload = {}                                        
    payload["sub"] = subject                            
    payload["iat"] = now                                
    payload["exp"] = now + EXP_REFRESH_TOKEN
    payload["typ"] = "refresh"                          
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)  
    return token  

def decode_jwt(token: str) -> dict:
    """
    Декодирует и валидирует JWT.
    Бросает исключение, если токен просрочен или подпись неверна.
    """

    data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    print(" decode_jwt отработал успешно")
    
    return data  





def verify_telegram_signature(payload: dict) -> bool:
    """
    Проверяет подпись данных, пришедших из Telegram Login Widget.
    Возвращает True при валидной подписи и свежем auth_date, иначе False.
    """
    
    data_copy = dict(payload)  

    
    received_hash = data_copy.pop("hash", None)  

   
    if received_hash is None:  
        return False  

    
    pairs = []  
    for key in sorted(data_copy.keys()):  
        value = data_copy[key]  
        pairs.append("{0}={1}".format(key, value))  
    data_check_string = "\n".join(pairs)  


    secret_key = hashlib.sha256(TELEGRAM_BOT_TOKEN.encode("utf-8")).digest()  

    
    calculated_hash = hmac.new(
        secret_key,  
        msg=data_check_string.encode("utf-8"), 
        digestmod=hashlib.sha256  
    ).hexdigest() 


    if not hmac.compare_digest(calculated_hash, received_hash):  
        return False  

    
    now = int(time.time())  
    auth_ts = int(data_copy.get("auth_date", 0))  
  
    if now - auth_ts > 180:  
        return False 

    return True  


def get_user_id_from_expired_token(token:str):
    """Получает анные из просроченного access токена, не вызывая исключений."""

    try:
        payload = jwt.decode(
                token, 
                JWT_SECRET, 
                algorithms=[JWT_ALG],
                options={"verify_signature": True, "verify_exp": False} 
            )

        user_id = payload.get("sub")
        return user_id

    except jwt.JWTError as e:
       
        print(f"Ошибка при декодировании истекшего токена: {e}")
        return None
