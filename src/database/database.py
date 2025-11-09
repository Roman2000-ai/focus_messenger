from sqlalchemy.ext.asyncio import async_session, create_async_engine,async_sessionmaker,AsyncSession
from src.database.models import Base
from src.config import   main_settings
import asyncio
import sys


DATABASE_URL = main_settings.database_url
DEBUG_DB = main_settings.debug_db


async_engine = create_async_engine(DATABASE_URL,echo=DEBUG_DB)
async_factory_session = async_sessionmaker(bind=async_engine,class_=AsyncSession,expire_on_commit=False)



async def create_tables():
    async with async_engine.connect() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def drop_tables():
    async with async_engine.connect() as conn:
        await conn.run_sync(Base.metadata.drop_all)



if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "create":
            asyncio.run(create_tables())
        elif sys.argv[1] == "drop":
            asyncio.run(drop_tables())
    else:
        print("Usage: python database.py create|drop")
