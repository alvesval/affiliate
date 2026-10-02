from datetime import datetime
from sqlalchemy import DateTime, String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base

class OAuthAttempt(Base):
    __tablename__ = "meli_oauth_attempts"
    company_id: Mapped[int|None] = mapped_column(Integer, nullable=True, index=True)
    state_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    verifier_encrypted: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[datetime] = mapped_column(DateTime)

class MercadoLivreOAuth(Base):
    __tablename__ = "meli_oauth_tokens"
    company_id: Mapped[int|None] = mapped_column(Integer, nullable=True, unique=True, index=True)
    id: Mapped[int] = mapped_column(primary_key=True)
    access_token_encrypted: Mapped[str] = mapped_column(Text)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    meli_user_id: Mapped[str] = mapped_column(String(80), default="")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
