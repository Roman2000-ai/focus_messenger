# -*- coding: utf-8 -*-

import os
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, FileResponse
from starlette.responses import RedirectResponse
import jwt
from telegram.telegram_functions import send_telegram_message
from telegram.telegram_verify import request_code_telegram,phone_verify_code,phone_verify_password
from config import TELEGRAM_BOT_TOKEN, JWT_SECRET  # noqa: F401
from schemas import MeOut,PhoneStartDTO,PhoneCodeDTO,PhonePwdDTO, MessageDTO
from depends import get_current_user_from_cookies, try_get_user
from security import (
    verify_telegram_signature,
    create_access_jwt,
    create_refresh_jwt,
    decode_jwt,
)
from database.crud import upsert_user_to_db,get_telethon_session,get_user_by_id

app = FastAPI()

WEB_DIR = os.path.join(os.path.dirname(__file__), "web")
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
TG_ALLOWED_KEYS = {"id", "first_name", "last_name", "username", "photo_url", "auth_date", "hash"}
templates = Jinja2Templates(directory=WEB_DIR)
@app.get("/")
async def root(request: Request, user=Depends(try_get_user)):
    print("работает функция root")
    if not user:
        return RedirectResponse(url="/welcome", status_code=302)

    id_user = user["sub"]
    session = await get_telethon_session(id_user)
    user = await get_user_by_id(id_user)
    return templates.TemplateResponse("index.html", {
        "request": request,   # важно: нужно для url_for
        "has_session": session,
        "user": user
    })



@app.get("/welcome")
async def welcome(request: Request, user=Depends(try_get_user)):
    print('работает функция welcome')
    if user:
        return RedirectResponse(url="/", status_code=302)
    return FileResponse(os.path.join(WEB_DIR, "login.html"))



@app.get("/auth/telegram-widget")
async def auth_telegram_widget(request: Request):
    print("работает функция auth_telegram_widget")
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
    resp.set_cookie("access_token", access_token, httponly=True, secure=True, samesite="lax", max_age=15*60, path="/")
    resp.set_cookie("refresh_token", refresh_token, httponly=True, secure=True, samesite="lax", max_age=30*24*60*60, path="/")
    return resp

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




@app.post("/auth/phone/start")
async def phone_start(dto:PhoneStartDTO, current=Depends(get_current_user_from_cookies)):
    print("работает функция phone_start")
    web_user_id = current["sub"]
    flow =  await request_code_telegram(dto,web_user_id)
    return flow

@app.post("/auth/phone/verify_code")
async def verify_code(dto:PhoneCodeDTO,current=Depends(get_current_user_from_cookies)):
    res = await phone_verify_code(dto)
    return res

@app.post("/auth/phone/verify_password")
async def verify_password(dto:PhonePwdDTO,current=Depends(get_current_user_from_cookies)):
    res = phone_verify_password(dto)
    return dto


@app.post("/telegram/send_message")
async def send_message(message_data:MessageDTO,current=Depends(get_current_user_from_cookies)):

    user_id = current["sub"]
    session = await get_telethon_session(user_id)
    
    message = message_data.message
    user = message_data.user
    res = await send_telegram_message(session.session,user,message)
    if not res:
        return {"success":False}
    return {"success": True}


@app.post("/logout")
async def logout(request: Request, user=Depends(try_get_user)):
    resp = RedirectResponse(url="/welcome", status_code=303)
    common = dict(path="/", samesite="lax", secure=True, httponly=True)
    resp.delete_cookie("access_token", **common)
    resp.delete_cookie("refresh_token", **common)
    resp.headers["Cache-Control"] = "no-store"
    return resp

