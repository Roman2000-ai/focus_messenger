import time    
import hmac     
import hashlib  
from typing import Dict  


import jwt  


from backend.config import TELEGRAM_BOT_TOKEN, JWT_SECRET, JWT_ALG  #


def verify_telegram_signature(payload: Dict) -> bool:
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



def create_access_jwt(user_id: int) -> str:
    """
    Создаёт наш собственный JWT для сессии приложения.
    Кладём sub=telegram_id, плюс стандартные метки iat/exp.
    """
   
    payload = {}  
    payload["sub"] = str(user_id)  
    payload["iat"] = int(time.time())  
    payload["exp"] = int(time.time()) + 3600 * 24 * 7 

    
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)  
    return token  

def create_refresh_jwt(subject: str, days: int = 30) -> str:
    """
    Создаёт долгоживущий refresh-JWT.
    """
    now = int(time.time())                              
    payload = {}                                        
    payload["sub"] = subject                            
    payload["iat"] = now                                
    payload["exp"] = now + 60 * 60 * 24 * days         
    payload["typ"] = "refresh"                          
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)  
    return token  

def decode_jwt(token: str) -> Dict:
    """
    Декодирует и валидирует JWT.
    Бросает исключение, если токен просрочен или подпись неверна.
    """

    data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    print(" decode_jwt отработал успешно")
    
    return data  


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
