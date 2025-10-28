import os
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, FileResponse
from starlette.responses import RedirectResponse
import jwt

from telegram.telegram_functions import send_telegram_message,get_data_telegram_contact,get_messages_from_dialog
from telegram.telegram_verify import request_code_telegram,phone_verify_code,phone_verify_password, qr_verify, _qr_wait, check_status_qr,check_2fa_qr,cancel_qr_login
from backend.config import TELEGRAM_BOT_TOKEN, JWT_SECRET, TELEGRAM_USERNAME  # noqa: F401
from backend.schemas import MeOut,PhoneStartDTO,PhoneCodeDTO,PhonePwdDTO, MessageDTO, QRstatusDTO,AddContactPayload,SendContactDTO,TwofaDTO,Flow_idDTO
from backend.depends import get_current_user_from_cookies, try_get_user
from backend.security import (
    verify_telegram_signature,
    create_access_jwt,
    create_refresh_jwt,
    decode_jwt,
    get_user_id_from_expired_token,
)
from database.crud import upsert_user_to_db,get_telethon_session,get_user_by_id,get_all_contacts_for_user,add_contact_to_db

app = FastAPI()

WEB_DIR = os.path.join(os.path.dirname(__file__), "../web")
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
TG_ALLOWED_KEYS = {"id", "first_name", "last_name", "username", "photo_url", "auth_date", "hash"}
templates = Jinja2Templates(directory=WEB_DIR)


#основная страница
@app.get("/")
async def root(request: Request, payload=Depends(try_get_user)):
    print("работает функция root")
    id_user = None
    has_session = False
    print(f"payload - {payload}")
    if payload:
        print("payload есть")
        id_user = payload["sub"]
        has_session = True
    else:
        print("попытка получить  просроченный токен")
        access_token_str = request.cookies.get("access_token")
        print(access_token_str)
        if access_token_str:
            print("токен access есть")
            id_user = get_user_id_from_expired_token(access_token_str)
            print(id_user)
            if id_user:
                print("токен  есть но  потухший")
                has_session = True
            else:
                has_session = False
            
        
    if not has_session:
        return RedirectResponse(url="/welcome", status_code=302)

    
    session = await get_telethon_session(id_user)
    user = await get_user_by_id(id_user)
    contacts = await get_all_contacts_for_user(id_user)
    return templates.TemplateResponse("index.html", {
        "request": request,   
        "has_session": session,
        'contacts': [SendContactDTO.model_validate(con).model_dump() for con in contacts],
        "user": user
    })
# страница авторизации
@app.get("/welcome")
async def welcome(request: Request, user=Depends(try_get_user)):
    if user:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse(
        "login.html", 
        {
            "request": request, 
            "TELEGRAM_USERNAME": TELEGRAM_USERNAME
        }
    )



#авториция через telegram-widget
@app.get("/auth/telegram-widget")
async def auth_telegram_widget(request: Request):
    raw = dict(request.query_params)
    params = {k: v for k, v in raw.items() if k in TG_ALLOWED_KEYS}

    rt = raw.get("return_to") or "/"
    return_to = rt if isinstance(rt, str) and rt.startswith("/") else "/"

    if not verify_telegram_signature(params):
        raise HTTPException(status_code=403, detail="Invalid Telegram signature or expired auth_date")
    
    user = await upsert_user_to_db(params)
    if not user:
        raise HTTPException(status_code=500, detail="Failed to upsert user")
    
    access_token = create_access_jwt(str(user.id))
    refresh_token = create_refresh_jwt(str(user.id), days=30)

    resp = RedirectResponse(url=return_to, status_code=302)
    resp.headers["Cache-Control"] = "no-store"
    resp.set_cookie("access_token", access_token, httponly=True, secure=True, samesite="lax", max_age=15*24*60*60, path="/")
    resp.set_cookie("refresh_token", refresh_token, httponly=True, secure=True, samesite="lax", max_age=30*24*60*60, path="/refresh")
    return resp


# получение сообщений
@app.get("/messages/{username:str}")
async def  get_messages(username, user=Depends(get_current_user_from_cookies)):
    user_id = user["sub"]
    session = await get_telethon_session(user_id)
    res, messages = await get_messages_from_dialog(session.session,username)
    if not res:
        return {"success":False,"message": "произошла ошибка в db"}
    return {"success":True,"messages": messages}

# добавление контакта
@app.post("/add_contact")
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

    







# обновление токена
@app.post("/refresh")
async def refresh(request: Request):
    refresh_token = request.cookies.get("refresh_token")
    if refresh_token is None:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    try:
        payload = decode_jwt(refresh_token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh")

    if payload.get("typ") not in (None, "refresh"):
        raise HTTPException(status_code=401, detail="Wrong token type")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Bad refresh payload")

    new_access = create_access_jwt(user_id)
    new_refresh = create_refresh_jwt(user_id, days=30)

    resp = JSONResponse({"ok": True})
    resp.headers["Cache-Control"] = "no-store"
    resp.set_cookie("access_token", new_access, httponly=True, secure=True, samesite="lax", max_age=15*60, path="/")
    resp.set_cookie("refresh_token", new_refresh, httponly=True, secure=True, samesite="lax", max_age=30*24*60*60, path="/")
    return resp

@app.get("/me", response_model=MeOut)
async def me(current=Depends(get_current_user_from_cookies)):
    return {"ok": True, "user": current}



#запрос в telegram api  для получения сессии если зашли через telgram widget
@app.post("/auth/phone/start")
async def phone_start(dto:PhoneStartDTO, current=Depends(get_current_user_from_cookies)):
    web_user_id = current["sub"]
    flow =  await request_code_telegram(dto,web_user_id)
    return flow
#отпрвления код  для логина на telegram api
@app.post("/auth/phone/verify_code")
async def verify_code(dto:PhoneCodeDTO,current=Depends(get_current_user_from_cookies)):
    res = await phone_verify_code(dto)
    return res
# получения  пароля если 2fa при авторизации на telegram api
@app.post("/auth/phone/verify_password")
async def verify_password(dto:PhonePwdDTO,current=Depends(get_current_user_from_cookies)):
    res =  await phone_verify_password(dto)
    return res
#логин через qr code(telethon) 
@app.post("/auth/qr")
async def  create_qr():
    print("работает функция create_qr")
    res  = await qr_verify()
    print(f"res = {res}")
    return res
#pooling  провери сканирования кода    
@app.post("/auth/qr/check")
async def check_qr(data:QRstatusDTO):
    print("работает функция  check_qr")
    state = await check_status_qr(data.flow_id)
    
    if state["status"] ==  "waiting":
            return {"status": "waiting"}

    if state["status"] == "error":
        return {"status":"error","message": state["message"]}
    if state["status"] =="2fa_required":
        return {"status": "2fa_required","message":state["message"]}
    if state["status"] == "authorized":
        user_id = state["user_id"]

        access_token = create_access_jwt(str(user_id))
        refresh_token = create_refresh_jwt(str(user_id), days=30)

        resp = JSONResponse({
            "status": "authorized",
            "redirect": "/" 
        })
        
    
        resp.headers["Cache-Control"] = "no-store"
        resp.set_cookie("access_token", access_token, httponly=True, secure=True, samesite="lax", max_age=15*60, path="/")
        resp.set_cookie("refresh_token", refresh_token, httponly=True, secure=True, samesite="lax", max_age=30*24*60*60, path="/")
        
        return resp


#получение пароля если 2fa при логине через qr 
@app.post("/auth/qr/2fa")
async def resume_2fa(data: TwofaDTO):

    flow_id  = data.flow_id
    password = data.password

    res = await check_2fa_qr(flow_id,password)
    return res


#отравление сообщения
@app.post("/telegram/send_message")
async def send_message(message_data:MessageDTO,current=Depends(get_current_user_from_cookies)):

    user_id = current["sub"]
    session = await get_telethon_session(user_id)
    
    message = message_data.message
    username = message_data.username
    res = await send_telegram_message(session.session,username,message)
    if not res:
        return {"success":False}
    return {"success": True}
# отмена логирования
@app.post("/auth/qr/cancel")
async def cancel_qr(data:Flow_idDTO):
    flow_id = data.flow_id
    res =  await cancel_qr_login(flow_id)
    return res
# выход из системы
@app.post("/logout")
async def logout(request: Request, user=Depends(try_get_user)):
    resp = RedirectResponse(url="/welcome", status_code=303)
    common = dict(path="/", samesite="lax", secure=True, httponly=True)
    resp.delete_cookie("access_token", **common)
    resp.delete_cookie("refresh_token", **common)
    resp.headers["Cache-Control"] = "no-store"
    return resp

