from dotenv import load_dotenv
import os
load_dotenv()
TELEGRAM_BOT_TOKEN= os.getenv("TELEGRAM_BOT_TOKEN")
JWT_SECRET=os.getenv("JWT_SECRET")
JWT_ALG=os.getenv("JWT_ALG")
FRONTEND_ORIGIN=os.getenv("FRONTENTD_ORIGIN")
DATABASE_URL=os.getenv("URL_ASYNC_DB")
API_HASH = os.getenv("API_HASH")
API_ID = os.getenv("API_ID")
TIMEOUT_WAITING_QR = float(os.getenv("TIMEOUT_WAITING_QR"))
TIMEOUT_2FA_INPUT = float(os.getenv("TIMEOUT_2FA_INPUT"))
DEBUG_DB = bool(os.getenv("DEBUG_DB",True))
TELEGRAM_USERNAME = os.getenv("TELEGRAM_USERNAME")

if TELEGRAM_BOT_TOKEN is None:  
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in .env")  # сразу падаем с понятной ошибкой

if JWT_SECRET is None:  
    raise RuntimeError("JWT_SECRET is not set in .env")  
