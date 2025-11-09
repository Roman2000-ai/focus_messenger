import os
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.responses import RedirectResponse
from src.telegram.router import router as telegram_router
from src.auth.router import router as auth_router
from src.depends import try_get_user
from src.auth.utils import get_user_id_from_expired_token
from src.config import main_settings
from src.telegram.config import telegram_settings
from src.database.crud import get_telethon_session, get_user_by_id, get_all_contacts_for_user
from src.telegram.schemas import SendContactDTO
from src.depends import get_current_user_from_cookies
from src.schemas import MeOut



app = FastAPI(
    docs_url=main_settings.docs_url,
    redoc_url=main_settings.redoc_url,
    openapi_url=main_settings.openapi_url,
)

app.include_router(telegram_router)
app.include_router(auth_router)


WEB_DIR = os.path.join(os.path.dirname(__file__), "../templates")

app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
templates = Jinja2Templates(directory=WEB_DIR)

TELEGRAM_USERNAME = telegram_settings.telegram_username_bot




#основная страница
@app.get("/")
async def root(request: Request, payload=Depends(try_get_user)):
    print("работает функция root")
    id_user = None
    has_session = False
    if payload:
        id_user = payload["sub"]
        has_session = True
    else:
        access_token_str = request.cookies.get("access_token")
        if access_token_str:
            id_user = get_user_id_from_expired_token(access_token_str)
            if id_user:
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
            "TELEGRAM_USERNAME_BOT": TELEGRAM_USERNAME
        }
    )


@app.get("/me", response_model=MeOut)
async def me(current=Depends(get_current_user_from_cookies)):
    return {"ok": True, "user": current}

# выход из системы
@app.post("/logout")
async def logout(request: Request, user=Depends(try_get_user)):
    resp = RedirectResponse(url="/welcome", status_code=303)
    common = dict(path="/", samesite="lax", secure=True, httponly=True)
    resp.delete_cookie("access_token", **common)
    resp.delete_cookie("refresh_token", **common)
    resp.headers["Cache-Control"] = "no-store"
    return resp

