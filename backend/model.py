from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import String, Date, DateTime, func,ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass


#四个表的ORM模型
class Transaction(Base):
    __tablename__ = "transactions"

    id:Mapped[int]=mapped_column(primary_key=True)
    account_id:Mapped[int]=mapped_column(ForeignKey("accounts.id"),nullable=False,)
    category_id:Mapped[int]=mapped_column(ForeignKey("categories.id"),nullable=False)
    user_id:Mapped[int]=mapped_column(ForeignKey("users.id"),nullable=False)

    money:Mapped[Decimal]=mapped_column(Numeric(9, 2), nullable=False)
    money_type:Mapped[str]=mapped_column(String(10), nullable=False)
    description:Mapped[str | None]=mapped_column(String(250))
    transaction_date:Mapped[date]=mapped_column(Date,nullable=False)
    created_at:Mapped[datetime]=mapped_column(DateTime,server_default=func.now(),nullable=False)

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(250), nullable=False)
    nickname: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"),nullable=False)
    name_accounts: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (UniqueConstraint("user_id", "name_categories"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"),nullable=False)
    name_categories: Mapped[str] = mapped_column(String(100), nullable=False)
    money_type: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        nullable=False
    )
