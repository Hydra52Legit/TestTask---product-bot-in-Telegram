from datetime import datetime
from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, DateTime, Text, BigInteger
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import Optional, List


class Base(DeclarativeBase):
    """Базовый класс для моделей SQLAlchemy"""
    pass


class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(100))
    first_name: Mapped[Optional[str]] = mapped_column(String(100))
    last_name: Mapped[Optional[str]] = mapped_column(String(100))
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    cards: Mapped[List["Card"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    purchases: Mapped[List["Purchase"]] = relationship(back_populates="user")
    withdrawal_requests: Mapped[List["WithdrawalRequest"]] = relationship(back_populates="user")


class Card(Base):
    """Модель карточки товара"""
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    photo_url: Mapped[Optional[str]] = mapped_column(String(500))
    photo_file_id: Mapped[Optional[str]] = mapped_column(String(500))
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    is_rejected: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))

    user: Mapped["User"] = relationship(back_populates="cards")
    purchases: Mapped[List["Purchase"]] = relationship(back_populates="card")


class Purchase(Base):
    """Модель покупки"""
    __tablename__ = "purchases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    invoice_id: Mapped[str] = mapped_column(String(100), unique=True)
    is_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    card_id: Mapped[int] = mapped_column(Integer, ForeignKey("cards.id"))

    user: Mapped["User"] = relationship(back_populates="purchases")
    card: Mapped["Card"] = relationship(back_populates="purchases")


class WithdrawalRequest(Base):
    """Модель заявки на вывод средств"""
    __tablename__ = "withdrawal_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    requisites: Mapped[str] = mapped_column(Text, nullable=False)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))

    user: Mapped["User"] = relationship(back_populates="withdrawal_requests")