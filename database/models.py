from sqlalchemy import BigInteger,func,ForeignKey,UniqueConstraint
from sqlalchemy.orm import Mapped,mapped_column,relationship,DeclarativeBase
import datetime


class Base(DeclarativeBase):
    def __repr__(self):
        cols = []
        for col in self.__table__.columns.keys():
            cols.append(f"{col}= {getattr(self,col)}")
        return f"<{self.__class__.__name__} {','.join(cols)}>"

class User(Base):
    __tablename__ = "users"
    id:Mapped[int] = mapped_column(primary_key=True,autoincrement=True)
    telegram_id:Mapped[int] = mapped_column(BigInteger,unique=True,nullable=False)
    username:Mapped[str] = mapped_column(nullable=True)
    first_name:Mapped[str] = mapped_column(nullable=True)
    last_name:Mapped[str] = mapped_column(nullable=True)
    photo_url:Mapped[str] = mapped_column(nullable=True)
    auth_date:Mapped[int] = mapped_column(nullable=True)
     # для telethon  session в будущем
    
    session: Mapped["SessionTelethon"] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False
    )
    chats: Mapped[list["Telegramchat"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )
    templates: Mapped[list["Shablon"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan"
    )


class SessionTelethon(Base):
    __tablename__ = "sessions"
    id:Mapped[int] = mapped_column(primary_key=True,autoincrement=True)
    user_id:Mapped[int] = mapped_column(ForeignKey("users.id",ondelete="CASCADE"),nullable=False,unique=True)
    session: Mapped[str] = mapped_column(nullable=False)

    user: Mapped[User] = relationship(back_populates="session")

class Telegramchat(Base):
    __tablename__ = "telegramchats"
    id: Mapped[int]  = mapped_column(primary_key=True,autoincrement=True)
    chat_id: Mapped[int] = mapped_column(nullable=False,unique=True)
    title: Mapped[str|None]
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id",ondelete="CASCADE"),nullable=False)
    chat_type: Mapped[str|None]
    username: Mapped[str|None]
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    user: Mapped[User] = relationship(back_populates="chats")


class Shablon(Base):
    __tablename__ = "shablons"
    id: Mapped[int]  = mapped_column(primary_key=True,autoincrement=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("telegramchats.id",ondelete="CASCADE"),nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id",ondelete="CASCADE"),nullable=False)
    text: Mapped[str] = mapped_column(nullable=False)

    user: Mapped[User] = relationship(back_populates="templates")
    chat: Mapped[Telegramchat] = relationship()

    __table_args__ = (
        UniqueConstraint("user_id", "chat_id", "text", name="uq_shablon_user_chat_text"),
    )

