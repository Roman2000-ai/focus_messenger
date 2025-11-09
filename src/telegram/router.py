from src.telegram.schemas import MessageDTO, AddContactPayload,SendContactDTO
from src.telegram.telegram_functions import send_telegram_message, get_messages_from_dialog, get_data_telegram_contact
from src.depends import get_current_user_from_cookies
from fastapi import Depends
from fastapi import APIRouter
from src.database.crud import get_telethon_session, add_contact_to_db

router = APIRouter(prefix="/telegram",tags=["telegram_functions"])

#отравление сообщения
@router.post("/send_message")
async def send_message(message_data:MessageDTO,current=Depends(get_current_user_from_cookies)):

    user_id = current["sub"]
    session = await get_telethon_session(user_id)
    
    message = message_data.message
    username = message_data.username
    res = await send_telegram_message(session.session,username,message)
    if not res:
        return {"success":False}
    return {"success": True}


# добавление контакта
@router.post("/add_contact")
async def add_contact(payload: AddContactPayload,user=Depends(get_current_user_from_cookies)):
    user_id = user["sub"]
    session = await get_telethon_session(user_id)
    success,data_user = await get_data_telegram_contact(session.session,payload.identifier,user_id)
    if not success:
        return {
            "success": False,
            "message": "ошибка при получении данных о  контакте" 
        }
    res,contact = await  add_contact_to_db(data_user,int(user_id))
    if res:
        contact_dto = SendContactDTO.model_validate(contact)
        return {"contact":contact_dto,"success": True, "message": "Контакт успешно добавлен."} # наверное нужно добавить dto для отправки  сообщения 

    return {"success":False, "message": "ошибка при добавлении в db"}



# получение сообщений
@router.get("/messages/{username:str}")
async def  get_messages(username, user=Depends(get_current_user_from_cookies)):
    user_id = user["sub"]
    session = await get_telethon_session(user_id)
    res, messages = await get_messages_from_dialog(session.session,username)
    if not res:
        return {"success":False,"message": "произошла ошибка в db"}
    return {"success":True,"messages": messages}