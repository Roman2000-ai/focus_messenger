from sqlalchemy.ext.asyncio import async_session, create_async_engine,async_sessionmaker,AsyncSession
from database.models import Base
from config import DATABASE_URL
import asyncio
import sys

print(DATABASE_URL)

async_engine = create_async_engine(DATABASE_URL,echo=True)
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
