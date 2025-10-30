from sqlalchemy.orm.util import state_class_str
import telethon
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PasswordHashInvalidError
import time

from fastapi import HTTPException
from backend.config import API_ID, API_HASH, TIMEOUT_2FA_INPUT ,TIMEOUT_WAITING_QR
import secrets
from typing import Dict
from database.crud  import  add_or_update_session_to_db,upsert_user_to_db
from backend.schemas import PhoneStartDTO,PhoneCodeDTO, PhonePwdDTO
import asyncio
from asyncio import TimeoutError as AsyncTimeoutError

PHONE_FLOWS: Dict[str, dict] = {}
USER_SESSIONS: Dict[str, str] = {}
QR_FLOWS: Dict = {}


def _gen_id() -> str:
    """генерация id для flow"""
    return secrets.token_urlsafe(18)

async def  request_code_telegram(data:PhoneStartDTO,web_user_id: str)->Dict[str,str]:
    """возвращает flow_id для дальнейшей авторизации"""
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



async def phone_verify_code(data:PhoneCodeDTO)-> dict:
    """проверка телефона телеграм и логине через телефон"""

    flow = PHONE_FLOWS.get(data.flow_id)
    if not flow:
        raise HTTPException(404, "flow not found")
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
        
        


async def phone_verify_password(data:PhonePwdDTO) -> dict:
    """ проверка пароля (2fa)"""


    flow = PHONE_FLOWS.get(data.flow_id)
    if not flow:
        raise HTTPException(404, "flow not found")
    if flow["stage"] != "2fa":
        raise HTTPException(400, f"unexpected stage: {flow['stage']}")

    client: telethon.TelegramClient = flow["client"]

    try:
        
        await client.sign_in(password=data.password)
        me = await client.get_me()
        print("успешно зашли с  помщью password")
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


async def qr_verify()-> dict:
    """верицикация с помощью  qr"""
    client = telethon.TelegramClient(StringSession(), API_ID, API_HASH)
    try:
        await client.connect()
        qr_log = await client.qr_login()
        flow_id = _gen_id()
        QR_FLOWS[flow_id] = {
            "client": client,
            "waiter": qr_log,
            "status":"waiting",
            "timestamp": time.time()
        }
        asyncio.create_task(_qr_wait(qr_log,client,flow_id))
        return {
            "flow_id": flow_id,
            "qr_url": qr_log.url
        }
    except Exception as e:
        print(f"Ошибка инициации QR-логина: {e}")
        await client.disconnect()
        return {'error': str(e)}


async def _qr_wait(qr_waiter,client,flow_id)-> None:
    """логика после того как отсканировали qr"""

  
    state = QR_FLOWS[flow_id]
        
    try:
        print('проверяем waiter ')
        await asyncio.wait_for(qr_waiter.wait(), timeout=300)
        print('waiter получен')
       
        
        new_session = client.session.save()
        web_user = await client.get_me()
        data_user = {}
        data_user["telegram_id"] = web_user.id
        data_user["username"] = getattr(web_user,'username',None)
        data_user["first_name"] = getattr(web_user,"first_name",None)
        data_user["last_name"] = getattr(web_user,"last_name",None)
        data_user["phone"] = getattr(web_user,"phone",None)
        data_user["photo_url"] = getattr(web_user,"photo_url",None)
        
        user = await upsert_user_to_db(data_user)
        session = await add_or_update_session_to_db(new_session,user.id)
        await client.disconnect()

        
        

        state['status'] = 'authorized' 
        state["user_id"] = user.id

        
        print(f"[{flow_id}] ✅ УСПЕХ: Сессия получена и сохранена.")
    except AsyncTimeoutError: 
        await client.disconnect()
        state['status'] = 'error'
        state['message'] = 'QR-код истек по времени (300с).'
        
    except SessionPasswordNeededError: 
        
        state["status"] = '2fa_required' 
        state['message'] = 'Требуется пароль облачной безопасности (2FA).'
        state["client"] =  client
        
    except Exception as e: 
        await client.disconnect()
        state['status'] = 'error' 
        state['message'] = f'Критическая ошибка: {e.__class__.__name__}'

async def check_status_qr(flow_id):
    """проверка состояния QR_FLOWS"""
    state = QR_FLOWS.get(flow_id)
    cur_time = time.time()
    timestamp = float(state["timestamp"])

    if state:
        if state['status'] == "authorized":
            state =  QR_FLOWS.pop(flow_id)
            return state
        if  state['status'] == "error":
            state = QR_FLOWS.pop(flow_id)
            return state
        if state["status"] == "waiting":
            timeout_duration = TIMEOUT_WAITING_QR
            
            if cur_time - timestamp > timeout_duration:
                state["status"] = "error"
                state['message'] = f"Таймаут истек ({timeout_duration} секунд). Поток удален."
                state = QR_FLOWS.pop(flow_id)
                return state
            return state

        if state["status"] == '2fa_required':
            timeout_duration = TIMEOUT_2FA_INPUT
            if cur_time - timestamp > timeout_duration:
                state["status"] = "error"
                state['message'] = f"Таймаут истек ({timeout_duration} секунд). Поток удален."
                state = QR_FLOWS.pop(flow_id)
                return state
            return state
    else:
        print("state не был найдет")


async  def check_2fa_qr(flow_id,password):
    """проверка пароля(2fa)"""
    try:
        state = QR_FLOWS.get(flow_id)
        client = state.get("client")
        if not state or state.get('status') != '2fa_required':
            return {'status': 'error', 'message': 'Неверный статус потока для ввода 2FA.'}
        result = await client.sign_in(
        password=password)
        print("мы вошли успешно с  помощью 2fa")
        
        
        new_session = client.session.save()
        web_user = await client.get_me()
        data_user = {}
        data_user["telegram_id"] = web_user.id
        data_user["username"] = getattr(web_user,'username',None)
        data_user["first_name"] = getattr(web_user,"first_name",None)
        data_user["last_name"] = getattr(web_user,"last_name",None)
        data_user["phone"] = getattr(web_user,"phone",None)
        data_user["photo_url"] = getattr(web_user,"photo_url",None)
        
        user = await upsert_user_to_db(data_user)
        print(f" получен user - {repr(user)}")
        session = await add_or_update_session_to_db(new_session,user.id)
        await client.disconnect()
        
        await client.disconnect()

        state['status'] = 'authorized' 
        state["user_id"] = user.id


        return {'status': 'success', 'message': 'Авторизация успешно завершена.'}
    except  PasswordHashInvalidError as e:
        print(f"ошибка - {e}")
        state["status"] = "2fa_required"
        state["message"] = "неправильный пароль 2fa"
        return {"status":"2fa_required","message":"неправильный пароль 2fa"}

    except Exception as e:
        print(f"ошибка - {e}") 
        await client.disconnect()
        state["status"] = "error"
        state['message'] = 'Критическая ошибка или таймаут сессии 2FA. Начните вход заново.'
        print(f"ошибка в  check_2fa_qr  ошибка -  {e}")
        return {"status":"error","message":'Критическая ошибка или таймаут сессии 2FA. Начните вход заново.'}








async def cancel_qr_login(temp_id: str) -> dict:
    """
    Позволяет фронтенду вручную отменить процесс QR-логина (например, 
    при нажатии кнопки "Отмена" в модальном окне).
    """
    state = QR_FLOWS.get(temp_id)
    if not state:
        return {'status': 'error', 'message': 'Сессия уже неактивна.'}

    client = state['client']
    
    try:
        await client.disconnect()
        del QR_FLOWS[temp_id]
        
        print(f"[{temp_id}] 🛑 Процесс отменен вручную.")
        return {'status': 'canceled', 'message': 'Процесс отменен.'}
    except Exception as e:
        print(f"[{temp_id}] Ошибка при отмене: {e}")
        return {'status': 'error', 'message': 'Ошибка при отмене процесса.'}