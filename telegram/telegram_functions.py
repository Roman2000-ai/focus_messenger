from telethon import TelegramClient
from telethon.sessions import StringSession
from backend.config import API_HASH,API_ID
from database.crud  import add_or_update_session_to_db
from datetime import datetime, timedelta, timezone
from typing import Tuple

async def  send_telegram_message(session: str, user: str, message: str)-> bool:
    """отправляет сообщение  telegram user"""
    try:
        async with TelegramClient(StringSession(session),API_ID,API_HASH) as client:
            entity =  await client.get_entity(user)
            print(entity)
            await client.send_message(entity,message)
            return True
    except Exception as e:
        print(f"произошла ошибка в send_message ошибка: {e}")
        return False
    




async def  get_data_telegram_contact(session:str,data_cont:str,user_id:str|int) -> Tuple:
    """ получает данные о контакте и добадяет его в db"""

    try:
        async with TelegramClient(StringSession(session),API_ID,API_HASH) as client:
            try:
                contact =  await client.get_entity(data_cont)

                data_contact = {}
                data_contact["telegram_id"] = contact.id
                data_contact["username"] = getattr(contact,'username',None)
                data_contact["first_name"] = getattr(contact,"first_name",None)
                data_contact["last_name"] = getattr(contact,"last_name",None)
                data_contact["photo_url"] = getattr(contact,"photo_url",None)
                data_contact["phone"] = getattr(contact,"number", None)
                new_session_str = client.session.save()
                session = await add_or_update_session_to_db(new_session_str,user_id)
                

                return True, data_contact
            except Exception as e:
                print(f'произошла ошибка в получения сущности в функции  get_data_telegram_contact, ошибка: {e}')
                return False, None
    except Exception as e:
                print(f'произошла ошибка в функции  get_data_telegram_contact, ошибка: {e}')
                return False , None      




async def get_messages_from_dialog(session: str, username: str, offset_houres: int = 12, fetch_limit: int = 200)-> Tuple:
    """получение  своих сообщниий из диалога"""
    recent_sent_messages = []
    offset_date = datetime.now(timezone.utc) - timedelta(hours=offset_houres)

    async with TelegramClient(StringSession(session), API_ID, API_HASH) as client:
        entity = await client.get_entity(username)

        messages = await client.get_messages(entity, limit=fetch_limit)

        for ind, message in enumerate(messages):
            if not message.date or not message.text:
                continue

            
            msg_date = message.date.replace(tzinfo=timezone.utc) if message.date.tzinfo is None else message.date

            if message.out and msg_date > offset_date:
                recent_sent_messages.append({
                    "id": message.id,
                    "date": msg_date.strftime('%Y-%m-%d %H:%M:%S UTC'),
                    "text": message.text
                })

        
        return True, recent_sent_messages

    return False, None