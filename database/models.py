from sqlalchemy import BigInteger, String, Boolean, Integer, DateTime, Index
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, DeclarativeBase, mapped_column
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from datetime import datetime

from config_data.config import Config, load_config

config: Config = load_config()
engine = create_async_engine(
    url=config.db.base_url,
)
async_session = async_sessionmaker(engine)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tg_id = mapped_column(BigInteger, unique=True)
    name: Mapped[str] = mapped_column(String(256))
    car_numbers: Mapped[list] = mapped_column(
        ARRAY(String(256)), nullable=True)
    track_number: Mapped[str] = mapped_column(String(256), nullable=True)
    type_car: Mapped[str] = mapped_column(String(256), nullable=True)
    border: Mapped[str] = mapped_column(String(256), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=True)
    tracking_type: Mapped[str] = mapped_column(String(256), nullable=True)
    tracking_interval: Mapped[int] = mapped_column(Integer, nullable=True)
    tracking_active: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=True)
    tracking_initial_order_id: Mapped[int] = mapped_column(
        Integer, nullable=True)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=True)
    call_queue_number: Mapped[int] = mapped_column(Integer, nullable=True)
    call_purchased: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=True)
    call_completed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=True)
    call_telegram_payment_charge_id: Mapped[str] = mapped_column(
        String(256), nullable=True)


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    payment_charge_id: Mapped[str] = mapped_column(String(256), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_type: Mapped[str] = mapped_column(
        String(20), nullable=False)  # "payment" или "refund"
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False)


class UserEvent(Base):
    __tablename__ = "user_events"

    id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, autoincrement=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True)
    event_data: Mapped[dict] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False, primary_key=True, index=True)

    __table_args__ = (
        Index('idx_user_events_tg_id_created_at', 'tg_id', 'created_at'),
    )


class MenuContent(Base):
    __tablename__ = "menu_contents"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
