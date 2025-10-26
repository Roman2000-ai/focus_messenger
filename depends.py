from security import decode_jwt
from fastapi import HTTPException,Request
from typing import Dict
import jwt


def get_current_user_from_cookies(request: Request) -> Dict:
    """
    Достаёт access_token из httpOnly-куки и валидирует его.
    """
    print("работает функция get_current_user_from_cookies")
    token = request.cookies.get("access_token")
    print(f'token - {token}')                   # забираем куку
    if token is None:                                                 # если нет
        raise HTTPException(status_code=401, detail="Missing access token")  # 401
    try:
        payload = decode_jwt(token)                                   #
    except jwt.ExpiredSignatureError:                                 # истёк
        raise HTTPException(status_code=401, detail="Access expired") # 401
    except jwt.InvalidTokenError:                                     # битый токен
        raise HTTPException(status_code=401, detail="Invalid access") # 401
    return payload    

async def try_get_user(request: Request):
    """Мягко получить пользователя: None вместо 401."""
    try:
        return  get_current_user_from_cookies(request)
    except HTTPException:
        return None