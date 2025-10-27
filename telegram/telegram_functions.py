from telethon import TelegramClient
from telethon.sessions import StringSession
from backend.config import API_HASH,API_ID
from database.crud  import add_or_update_session_to_db
from datetime import datetime, timedelta, timezone


async def  send_telegram_message(session: str, user: str, message: str)-> bool:
    """отправляет сообщение  telegram user"""
    print("рабоет функция  send_telegram_message")
    try:
        async with TelegramClient(StringSession(session),API_ID,API_HASH) as client:
            try:
                entity =  await client.get_entity(user)
                print("получена  сущность  по  peer_id")
                print(entity)
                await client.send_message(entity,message)
                return True
            except Exception as e:
                print(f"сообщение не было отправлено ошибка {e}")
                return False
    except Exception as e:
        print(f"произошла ошибка в send_message ошибка: {e}")
        return False
    




async def  get_data_telegram_contact(session:str,data_cont:str,user_id:str|int):
    """ получает данные о контакте и добадяет его в db"""

    try:
        async with TelegramClient(StringSession(session),API_ID,API_HASH) as client:
            try:
                contact =  await client.get_entity(data_cont)
                print(contact)

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



# async def  get_messages_from_dialog(session : str,username: str,offset_houres: int =12,fetch_limit: int = 200):
#     print("Работает функция  get_messages_from_dialog")
#     recent_sent_messages = []
    
#     offset_date = datetime.now(timezone.utc) - timedelta(hours=offset_houres)


#     async with TelegramClient(StringSession(session),API_ID,API_HASH) as client:

#         entity = await client.get_entity(username)

#         messages = await client.get_messages(
#                 entity, 
#                 limit=fetch_limit,
#             )
#         print(f" len message - {len(messages)}")
#         for ind ,message in enumerate(messages):
            
          
            
#             if not message.date or not message.text:
#                 print(f"iteration -{ind}")
#                 print("отработал continue")
#                 continue
                
            
#             if message.out and message.date > offset_date:
#                 print("отработал  добавление сообщения в список")
#                 recent_sent_messages.append({
#                     "id": message.id,
#                     "date": message.date.strftime('%Y-%m-%d %H:%M:%S UTC'),
#                     "text": message.text
#                 })
               
                
                
#         print(recent_sent_messages)
#         return True, recent_sent_messages   
#     return False , None

async def get_messages_from_dialog(session: str, username: str, offset_houres: int = 12, fetch_limit: int = 200):
    print("Работает функция get_messages_from_dialog")

    recent_sent_messages = []
    offset_date = datetime.now(timezone.utc) - timedelta(hours=offset_houres)
    print(f"Ищем сообщения новее: {offset_date}")

    async with TelegramClient(StringSession(session), API_ID, API_HASH) as client:
        entity = await client.get_entity(username)

        messages = await client.get_messages(entity, limit=fetch_limit)
        print(f"Всего получено сообщений: {len(messages)}")

        for ind, message in enumerate(messages):
            if not message.date or not message.text:
                continue

            # 🕒 Приведение к UTC
            msg_date = message.date.replace(tzinfo=timezone.utc) if message.date.tzinfo is None else message.date

            # 📨 Фильтруем только исходящие за последние 12 часов
            if message.out and msg_date > offset_date:
                recent_sent_messages.append({
                    "id": message.id,
                    "date": msg_date.strftime('%Y-%m-%d %H:%M:%S UTC'),
                    "text": message.text
                })

        print(f"Найдено сообщений за последние {offset_houres} часов: {len(recent_sent_messages)}")
        return True, recent_sent_messages

    return False, None