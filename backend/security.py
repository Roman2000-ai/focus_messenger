import time     # для работы со временем (метки iat/exp и проверка давности auth_date)
import hmac     # для расчёта HMAC
import hashlib  # для SHA256 и производных
from typing import Dict  # подсказка типа словаря

# Импорт внешних библиотек
import jwt  # библиотека PyJWT для кодирования/декодирования JWT

# Импорт наших настроек
from backend.config import TELEGRAM_BOT_TOKEN, JWT_SECRET, JWT_ALG  #


def verify_telegram_signature(payload: Dict) -> bool:
    """
    Проверяет подпись данных, пришедших из Telegram Login Widget.
    Возвращает True при валидной подписи и свежем auth_date, иначе False.
    """
    
    data_copy = dict(payload)  # создаём поверхностную копию

    
    received_hash = data_copy.pop("hash", None)  # получить хеш и убрать из данных

   
    if received_hash is None:  
        return False  

    # Собираем data-check-string: сортируем ключи и делаем строки вида "key=value"
    pairs = []  # список, куда будем класть "key=value"
    for key in sorted(data_copy.keys()):  # алфавитный порядок ключей
        value = data_copy[key]  # берём значение по ключу
        pairs.append("{0}={1}".format(key, value))  # добавляем строку без f-строки
    data_check_string = "\n".join(pairs)  # соединяем строки переводом строки

    # Секретный ключ для HMAC = SHA256(TELEGRAM_BOT_TOKEN)
    secret_key = hashlib.sha256(TELEGRAM_BOT_TOKEN.encode("utf-8")).digest()  # бинарный ключ

    # Считаем HMAC-SHA256(data_check_string, secret_key) и берём hex-представление
    calculated_hash = hmac.new(
        secret_key,  # ключ HMAC
        msg=data_check_string.encode("utf-8"),  # байтовое сообщение
        digestmod=hashlib.sha256  # алгоритм SHA256
    ).hexdigest()  # hex-строка результата

    # Сравниваем безопасным методом, устойчивым к тайминговым атакам
    if not hmac.compare_digest(calculated_hash, received_hash):  # если подпись не совпала
        return False  # возвращаем False

    # Дополнительная защита: проверяем свежесть auth_date
    now = int(time.time())  # текущее UNIX-время
    auth_ts = int(data_copy.get("auth_date", 0))  # читаем метку времени из данных
    # Разумное окно 120 секунд; при необходимости увеличьте
    if now - auth_ts > 120:  # если данные слишком старые
        return False  # считаем недействительными

    # Если дошли сюда — подпись корректна и данные свежие
    return True  # всё хорошо



def create_access_jwt(user_id: int) -> str:
    """
    Создаёт наш собственный JWT для сессии приложения.
    Кладём sub=telegram_id, плюс стандартные метки iat/exp.
    """
    # Полезная нагрузка токена
    payload = {}  # создаём словарь для claims
    payload["sub"] = str(user_id)  # subject — идентификатор пользователя в виде строки
    payload["iat"] = int(time.time())  # время выпуска токена
    payload["exp"] = int(time.time()) + 3600 * 24 * 7  # срок действия (7 дней)

    # Кодируем токен нашим секретом и алгоритмом
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)  # получаем строку JWT
    return token  # возвращаем строковый токен

def create_refresh_jwt(subject: str, days: int = 30) -> str:
    """
    Создаёт долгоживущий refresh-JWT.
    В реальном проде лучше хранить refresh-токены в БД (хеш), но пока делаем просто JWT.
    """
    now = int(time.time())                              # текущее время
    payload = {}                                        # claims
    payload["sub"] = subject                            # идентификатор пользователя
    payload["iat"] = now                                # время выпуска
    payload["exp"] = now + 60 * 60 * 24 * days         # срок годности (дни)
    payload["typ"] = "refresh"                          # помечаем тип (необязательно, но удобно)
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)  # подпись
    return token  

def decode_jwt(token: str) -> Dict:
    """
    Декодирует и валидирует JWT.
    Бросает исключение, если токен просрочен или подпись неверна.
    """
    print(f"access-token - {token}")
    print("работает decode_jwt")
    data = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    print(" decode_jwt отработал успешно")
    print(type(data))
    for key, value in data.items():
        print(f'{key} - {value}') 
    return data  


def get_user_id_from_expired_token(token:str):

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
