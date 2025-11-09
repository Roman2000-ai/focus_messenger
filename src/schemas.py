from pydantic import BaseModel


class MeOut(BaseModel):
    """
    Ответ защищённого эндпоинта /me (минимальная форма).
    """
    ok: bool  
    user: dict 
