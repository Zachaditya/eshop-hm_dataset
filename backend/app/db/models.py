from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, ForeignKey, Text,
    CheckConstraint, UniqueConstraint, Index, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from app.core.db import Base
from sqlalchemy.sql import and_
from uuid import uuid4


class Product(Base):
    __tablename__ = "products"

    # Primary key = article_id
    id: Mapped[str] = mapped_column(String, primary_key=True)  # article_id

    # ---- Convenience fields (keep these for your existing API/UI) ----
    name: Mapped[str] = mapped_column(String, nullable=False)                 # prod_name
    category: Mapped[str | None] = mapped_column(String, nullable=True)       # product_group_name (or index_group_name)
    price: Mapped[float | None] = mapped_column(Float, nullable=True)         # price_cents / 100
    description: Mapped[str | None] = mapped_column(Text, nullable=True)      # detail_desc
    color: Mapped[str | None] = mapped_column(String, nullable=True)          # colour_group_name

    image_key: Mapped[str | None] = mapped_column(String, nullable=True)
    has_image: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ---- Full CSV columns ----
    product_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    prod_name: Mapped[str | None] = mapped_column(String, nullable=True)

    product_type_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    product_type_name: Mapped[str | None] = mapped_column(String, nullable=True)

    product_group_name: Mapped[str | None] = mapped_column(String, nullable=True)

    graphical_appearance_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    graphical_appearance_name: Mapped[str | None] = mapped_column(String, nullable=True)

    colour_group_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    colour_group_name: Mapped[str | None] = mapped_column(String, nullable=True)

    perceived_colour_value_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    perceived_colour_value_name: Mapped[str | None] = mapped_column(String, nullable=True)

    perceived_colour_master_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    perceived_colour_master_name: Mapped[str | None] = mapped_column(String, nullable=True)

    department_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    department_name: Mapped[str | None] = mapped_column(String, nullable=True)

    index_code: Mapped[str | None] = mapped_column(String, nullable=True)
    index_name: Mapped[str | None] = mapped_column(String, nullable=True)

    index_group_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    index_group_name: Mapped[str | None] = mapped_column(String, nullable=True)

    section_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section_name: Mapped[str | None] = mapped_column(String, nullable=True)

    garment_group_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    garment_group_name: Mapped[str | None] = mapped_column(String, nullable=True)

    detail_desc: Mapped[str | None] = mapped_column(Text, nullable=True)

    price_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str | None] = mapped_column(String, nullable=True)

class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    session_id: Mapped[str] = mapped_column(String, nullable=False)

    product_id: Mapped[str] = mapped_column(String, ForeignKey("products.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)  # view|add_to_cart|purchase|remove
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: uuid4().hex
    )
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)


    # keep this for now even if you remove password UI
    password_hash: Mapped[str] = mapped_column(String, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    carts: Mapped[list["Cart"]] = relationship("Cart", back_populates="user")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid4().hex)

    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    token_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)



class Cart(Base):
    __tablename__ = "carts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid4().hex)

    # null means guest cart
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    status: Mapped[str] = mapped_column(String, nullable=False, server_default="active")

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    user: Mapped["User | None"] = relationship("User", back_populates="carts")
    items: Mapped[list["CartItem"]] = relationship(
        "CartItem", back_populates="cart", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("status IN ('active','ordered','merged','abandoned')", name="ck_carts_status"),

        # One ACTIVE cart per logged-in user (guest carts have user_id NULL)
        Index(
            "ux_carts_one_active_per_user",
            "user_id",
            unique=True,
            sqlite_where=and_(user_id.isnot(None), status == "active"),
        ),

        Index("ix_carts_user_id", "user_id"),
    )


class CartItem(Base):
    __tablename__ = "cart_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: uuid4().hex)
    cart_id: Mapped[str] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"), nullable=False, index=True)

    product_id: Mapped[str] = mapped_column(String, ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    # Optional snapshot. Leave null if you don’t want this yet.
    unit_price_cents: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    cart: Mapped["Cart"] = relationship("Cart", back_populates="items")

    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_cart_items_quantity"),
        CheckConstraint("unit_price_cents IS NULL OR unit_price_cents >= 0", name="ck_cart_items_unit_price"),
        UniqueConstraint("cart_id", "product_id", name="ux_cart_items_cart_product"),
    )

