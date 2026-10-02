from datetime import datetime
from sqlalchemy import String, Float, ForeignKey, DateTime, Integer, UniqueConstraint, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base
class User(Base):
    __tablename__="users"
    id: Mapped[int]=mapped_column(primary_key=True)
    email: Mapped[str]=mapped_column(String(180), unique=True, index=True)
    name: Mapped[str]=mapped_column(String(120))
class Product(Base):
    __tablename__="products"
    company_id: Mapped[int|None]=mapped_column(Integer, nullable=True, index=True)
    __table_args__ = (UniqueConstraint("company_id", "marketplace", "external_id", name="uq_product_company_marketplace_external"),)
    id: Mapped[int]=mapped_column(primary_key=True)
    image_url: Mapped[str]=mapped_column(String(2000), default="")
    permalink: Mapped[str]=mapped_column(String(2000), default="")
    source: Mapped[str]=mapped_column(String(40), default="manual")
    synced_at: Mapped[datetime | None]=mapped_column(DateTime, nullable=True)
    marketplace: Mapped[str]=mapped_column(String(30), index=True)
    external_id: Mapped[str]=mapped_column(String(100), index=True)
    title: Mapped[str]=mapped_column(String(300))
    category: Mapped[str]=mapped_column(String(100), default="Geral")
    price: Mapped[float]=mapped_column(Float, default=0)
    original_price: Mapped[float]=mapped_column(Float, default=0)
    commission_rate: Mapped[float]=mapped_column(Float, default=0)
    affiliate_url: Mapped[str]=mapped_column(String(1000), default="")
    affiliate_label: Mapped[str]=mapped_column(String(120), default="")
    affiliate_source: Mapped[str]=mapped_column(String(40), default="")
    affiliate_verified_at: Mapped[datetime | None]=mapped_column(DateTime, nullable=True)
class ProductPrice(Base):
    __tablename__="product_prices"
    company_id: Mapped[int|None]=mapped_column(Integer, nullable=True, index=True)
    id: Mapped[int]=mapped_column(primary_key=True)
    product_id: Mapped[int]=mapped_column(ForeignKey("products.id"), index=True)
    price: Mapped[float]=mapped_column(Float)
    captured_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)
class ProductScore(Base):
    __tablename__="product_scores"
    company_id: Mapped[int|None]=mapped_column(Integer, nullable=True, index=True)
    id: Mapped[int]=mapped_column(primary_key=True)
    product_id: Mapped[int]=mapped_column(ForeignKey("products.id"), index=True)
    score: Mapped[float]=mapped_column(Float)
    expected_commission: Mapped[float]=mapped_column(Float)
    calculated_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class ProductContent(Base):
    company_id: Mapped[int|None] = mapped_column(Integer, nullable=True, index=True)
    __tablename__ = "product_contents"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    channel: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(300))
    hook: Mapped[str] = mapped_column(String(500))
    caption: Mapped[str] = mapped_column(Text)
    script: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
