from database.database import async_factory_session
from database.models import User, SessionTelethon, Contact
from backend.schemas import UserDB
from sqlalchemy import select
from typing import Tuple







async def upsert_user_to_db(user:dict)-> User|None:
    """обновление или добавление user в db"""
    dto = UserDB(**user)

    try:
        async with async_factory_session() as session:
            existing = (await session.execute(select(User).where(User.telegram_id == dto.telegram_id))).scalar_one_or_none()
            if existing:
                existing.first_name = dto.first_name
                existing.last_name = dto.last_name
                existing.username = dto.username
                existing.photo_url = dto.photo_url
                existing.auth_date = dto.auth_date
                existing.phone = dto.phone
                await session.flush()
                await session.commit()
                print(f"{repr(existing)} был обновлен")
                return existing
            user_orm = User(**dto.model_dump())
            session.add(user_orm)
            await session.commit()
            await session.refresh(user_orm)
            print(f"{repr(user_orm)}   был добвлен в db")
            return user_orm

    except Exception as e:
        print(f"произошла ошибка в функции add_user_to_db ошибка:\n{e}")
        return None

async def get_user_by_id(id: int) -> User|None:
    """получения user по id"""
    async with async_factory_session() as session:
        query = select(User).where(User.id == id)
        res = await session.execute(query)
        user = res.scalar_one_or_none()
        return user

async def add_or_update_session_to_db(session_telethon:str,user_id:int)-> bool:
    """добавление или обновление session в db"""

    try:
        async with async_factory_session() as session:
           async with session.begin(): 
              
                existing = (await session.execute(
                    select(SessionTelethon).where(SessionTelethon.user_id == user_id)
                )).scalar_one_or_none()

                if existing:
                    print("сессия существует,идет обновление")
                    existing.session = session_telethon  
                    return True 
                    
                else:
                    session.add(SessionTelethon(user_id=user_id, session=session_telethon))
                    return True
                    
    except Exception as e:
        print(f"произошла ошибка в функции add_or_update_session_to_db ошибка:\n {e}")
        return False

    



async def get_telethon_session(user_id: int)-> SessionTelethon|None: 
    """получение сессии с помощью user_id для работы в telethon"""
    async with async_factory_session() as session:

        query = select(SessionTelethon).where(SessionTelethon.user_id == user_id)

        res = await session.execute(query)

        session = res.scalar_one_or_none()

        if not session:
            return None

        return session


async def get_all_contacts_for_user(user_id: int|str)-> list[Contact]:
    """получение contacts с помощью  user_id"""

    user_id = int(user_id)
    query = select(Contact).where(Contact.user_id==user_id)

    async with async_factory_session() as session:
        res = await session.execute(query)

        contacts = res.scalars().all()

        return contacts


async def add_contact_to_db(data_user: dict,user_id: str|int)-> Tuple:
    """ добавление contacts   в db"""
    async with async_factory_session() as session:
        existing =   ( await session.execute(select(Contact).where(Contact.telegram_id == data_user["telegram_id"]))).scalar_one_or_none()
        if existing:
            print('contact  already exists')
            return False, "exist"
        
        contact_orm =  Contact(**data_user,user_id=user_id)

        session.add(contact_orm)
        await session.commit()

        await session.refresh(contact_orm)

        print(f"{contact_orm} был добавлен в db")
        return True, contact_orm
    




