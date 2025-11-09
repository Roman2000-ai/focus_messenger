#возможно depends для получния get user_form coockie  здесь не нужны  надо будет поверить
from fastapi import APIRouter, Request , HTTPException,Depends
from fastapi.responses import JSONResponse
from starlette.responses import RedirectResponse
from src.auth.utils import verify_telegram_signature, create_access_jwt, create_refresh_jwt, decode_jwt
from src.auth.config import auth_settings
from src.auth.schemas import PhoneStartDTO, PhoneCodeDTO, PhonePwdDTO, QRstatusDTO, TwofaDTO, Flow_idDTO
from src.database.crud import upsert_user_to_db
from src.telegram.telegram_verify import  request_code_telegram,phone_verify_code,phone_verify_password,qr_verify,check_status_qr,check_2fa_qr,cancel_qr_login
from src.depends import get_current_user_from_cookies
import jwt




router = APIRouter(prefix="/auth",tags=["Authentication"]) 


#авториция через telegram-widget
@router.get("/telegram-widget")
async def auth_telegram_widget(request: Request):
    raw = dict(request.query_params)
    params = {k: v for k, v in raw.items() if k in auth_settings.tg_allowed_keys}

    rt = raw.get("return_to") or "/"
    return_to = rt if isinstance(rt, str) and rt.startswith("/") else "/"

    if not verify_telegram_signature(params):
        raise HTTPException(status_code=403, detail="Invalid Telegram signature or expired auth_date")
    
    user = await upsert_user_to_db(params)
    if not user:
        raise HTTPException(status_code=500, detail="Failed to upsert user")
    
    access_token = create_access_jwt(str(user.id))
    refresh_token = create_refresh_jwt(str(user.id))

    resp = RedirectResponse(url=return_to, status_code=302)
    resp.headers["Cache-Control"] = "no-store"
    resp.set_cookie("access_token", access_token, httponly=True, secure=True, samesite="lax", max_age=15*24*60*60, path="/")
    resp.set_cookie("refresh_token", refresh_token, httponly=True, secure=True, samesite="lax", max_age=30*24*60*60, path="/refresh")
    return resp



#запрос в telegram api  для получения сессии если зашли через telgram widget
@router.post("/phone/start")
async def phone_start(dto:PhoneStartDTO, current=Depends(get_current_user_from_cookies)):
    web_user_id = current["sub"]
    flow =  await request_code_telegram(dto,web_user_id)
    return flow
#отпрвления код  для логина на telegram api
@router.post("/phone/verify_code")
async def verify_code(dto:PhoneCodeDTO,current=Depends(get_current_user_from_cookies)):
    res = await phone_verify_code(dto)
    return res
# получения  пароля если 2fa при авторизации на telegram api
@router.post("/phone/verify_password")
async def verify_password(dto:PhonePwdDTO,current=Depends(get_current_user_from_cookies)):
    res =  await phone_verify_password(dto)
    return res
#логин через qr code(telethon) 
@router.post("/qr")
async def  create_qr():
    print("работает функция create_qr")
    res  = await qr_verify()
    return res
#pooling  провери сканирования кода    
@router.post("/qr/check")
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
        refresh_token = create_refresh_jwt(str(user_id))

        resp = JSONResponse({
            "status": "authorized",
            "redirect": "/" 
        })
        
    
        resp.headers["Cache-Control"] = "no-store"
        resp.set_cookie("access_token", access_token, httponly=True, secure=True, samesite="lax", max_age=15*60, path="/")
        resp.set_cookie("refresh_token", refresh_token, httponly=True, secure=True, samesite="lax", max_age=30*24*60*60, path="/")
        
        return resp


#получение пароля если 2fa при логине через qr 
@router.post("/qr/2fa")
async def resume_2fa(data: TwofaDTO):

    flow_id  = data.flow_id
    password = data.password

    res = await check_2fa_qr(flow_id,password)
    return res


@router.post("/qr/cancel")
async def cancel_qr(data:Flow_idDTO):
    flow_id = data.flow_id
    res =  await cancel_qr_login(flow_id)
    return res


# обновление токена
# в будущем можно  вынести логику проврки в utils 
@router.post("/refresh")
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
    new_refresh = create_refresh_jwt(user_id)

    resp = JSONResponse({"ok": True})
    resp.headers["Cache-Control"] = "no-store"
    resp.set_cookie("access_token", new_access, httponly=True, secure=True, samesite="lax", max_age=15*60, path="/")
    resp.set_cookie("refresh_token", new_refresh, httponly=True, secure=True, samesite="lax", max_age=30*24*60*60, path="/")
    return resp

