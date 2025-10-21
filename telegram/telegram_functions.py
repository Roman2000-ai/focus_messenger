from telethon import TelegramClient
from telethon.sessions import StringSession
from config import API_HASH,API_ID




async def  send_telegram_message(session: str, user: str, message: str)-> bool:
    """отправляет сообщение  telegram user"""
    try:
        async with TelegramClient(StringSession(session),API_ID,API_HASH) as client:
            try:
                await client.send_message(user,message)
                return True
            except Exception as e:
                print(f"сообщение не было отправлено ошибка {e}")
                return False
    except Exception as e:
        print(f"произошла ошибка в send_message ошибка: {e}")
        return False
    

