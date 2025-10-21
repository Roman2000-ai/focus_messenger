import telethon
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError 
from fastapi import HTTPException
from config import API_ID, API_HASH
import secrets
from typing import Dict
from database.crud  import  add_or_update_session_to_db
from schemas import PhoneStartDTO,PhoneCodeDTO, PhonePwdDTO

PHONE_FLOWS: Dict[str, dict] = {}
USER_SESSIONS: Dict[str, str] = {}


def _gen_id() -> str:
    # Генерим безопасный короткий id для flow_id
    return secrets.token_urlsafe(18)

async def  request_code_telegram(data:PhoneStartDTO,web_user_id: str)->Dict[str,str]:
    """возвращает flow_id для дальнейшей авторизации"""
    print("работает функция request_code-telegram")
    client = telethon.TelegramClient(StringSession(), API_ID, API_HASH)
   
    await client.connect()
  
    try:
         await client.send_code_request(data.phone)

    except Exception as e:
        print(f"произошла ошибка в request_code_telegram ошибка : {e}")
        await client.disconnect()
        raise HTTPException(400, f"send_code_request failed: {e}")

    flow_id = _gen_id()
    PHONE_FLOWS[flow_id] = {
        "client": client,           
        "phone": data.phone,         
        "stage": "code",            
        "web_user_id": web_user_id,  
    }
   
    return {"flow_id": flow_id}



async def phone_verify_code(data:PhoneCodeDTO):

    flow = PHONE_FLOWS.get(data.flow_id)
    if not flow:
        raise HTTPException(404, "flow not found")
    # 2. Проверяем ожидаемую стадию.
    if flow["stage"] != "code":
        raise HTTPException(400, f"unexpected stage: {flow['stage']}")

    client: telethon.TelegramClient = flow["client"]
    try:
        await client.sign_in(phone=flow["phone"], code=data.code)
        me = await client.get_me()
        session_str = client.session.save()
        res = await add_or_update_session_to_db(session_str,int(flow["web_user_id"]))
        if not res:
            try:
                await client.disconnect()
            finally:
                PHONE_FLOWS.pop(data.flow_id, None)
            raise HTTPException(500, "failed to persist session")
        
        flow["stage"] = "done"
        await client.disconnect()
        PHONE_FLOWS.pop(data.flow_id, None)
        return {"ok": True, "user": {"id": me.id, "username": me.username}}

    except SessionPasswordNeededError:
        flow["stage"] = "2fa"
        return {"ok": False, "need_2fa": True}

    except Exception as e:
        try:
            await client.disconnect()
            
            
        finally:
            PHONE_FLOWS.pop(data.flow_id, None)
        raise HTTPException(400, f"sign_in failed: {e}")
        
        


async def phone_verify_password(data:PhonePwdDTO):


    flow = PHONE_FLOWS.get(data.flow_id)
    if not flow:
        raise HTTPException(404, "flow not found")
    if flow["stage"] != "2fa":
        raise HTTPException(400, f"unexpected stage: {flow['stage']}")

    client: telethon.TelegramClient = flow["client"]

    try:
        
        await client.sign_in(password=data.password)
        me = await client.get_me()
        session_str = client.session.save()
        res = await add_or_update_session_to_db(session_str,int(flow["web_user_id"]))
        if not res:
            try:
                await client.disconnect()
            finally:
                PHONE_FLOWS.pop(data.flow_id, None)
            raise HTTPException(500, "failed to persist session")

        USER_SESSIONS[flow["web_user_id"]] = session_str
        flow["stage"] = "done"
        await client.disconnect()
        PHONE_FLOWS.pop(data.flow_id, None)
        return {"ok": True, "user": {"id": me.id, "username": me.username}}

    except Exception as e:
        
        try:
            await client.disconnect()
        finally:
            PHONE_FLOWS.pop(data.flow_id, None)
        raise HTTPException(400, f"2FA failed: {e}")


