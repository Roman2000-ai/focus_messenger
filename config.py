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

if TELEGRAM_BOT_TOKEN is None:  
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in .env")  # сразу падаем с понятной ошибкой

if JWT_SECRET is None:  
    raise RuntimeError("JWT_SECRET is not set in .env")  
