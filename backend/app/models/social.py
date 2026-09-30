from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base

class SocialConnection(Base):
    __tablename__='social_connections'
    id: Mapped[int]=mapped_column(primary_key=True)
    platform: Mapped[str]=mapped_column(String(30), unique=True, index=True)
    account_name: Mapped[str]=mapped_column(String(180), default='')
    external_user_id: Mapped[str]=mapped_column(String(180), default='')
    access_token_enc: Mapped[str]=mapped_column(Text, default='')
    refresh_token_enc: Mapped[str]=mapped_column(Text, default='')
    scopes: Mapped[str]=mapped_column(Text, default='')
    expires_at: Mapped[datetime|None]=mapped_column(DateTime, nullable=True)
    connected_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class SocialOAuthAttempt(Base):
    __tablename__='social_oauth_attempts'
    id: Mapped[int]=mapped_column(primary_key=True)
    platform: Mapped[str]=mapped_column(String(30), index=True)
    state: Mapped[str]=mapped_column(String(180), unique=True, index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class ContentCampaign(Base):
    __tablename__='content_campaigns'
    id: Mapped[int]=mapped_column(primary_key=True)
    product_id: Mapped[int]=mapped_column(ForeignKey('products.id'), index=True)
    name: Mapped[str]=mapped_column(String(300))
    objective: Mapped[str]=mapped_column(String(30), default='Venda')
    format: Mapped[str]=mapped_column(String(30), default='Vídeo curto')
    duration_seconds: Mapped[int]=mapped_column(Integer, default=30)
    tone: Mapped[str]=mapped_column(String(60), default='Direto e acessível')
    audience: Mapped[str]=mapped_column(String(200), default='')
    status: Mapped[str]=mapped_column(String(30), default='draft')
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class ContentVariant(Base):
    __tablename__='content_variants'
    id: Mapped[int]=mapped_column(primary_key=True)
    campaign_id: Mapped[int]=mapped_column(ForeignKey('content_campaigns.id'), index=True)
    platform: Mapped[str]=mapped_column(String(30), index=True)
    title: Mapped[str]=mapped_column(String(300))
    hook: Mapped[str]=mapped_column(String(500))
    caption: Mapped[str]=mapped_column(Text)
    script: Mapped[str]=mapped_column(Text)
    hashtags: Mapped[str]=mapped_column(Text, default='')
    cta: Mapped[str]=mapped_column(String(500), default='')
    media_url: Mapped[str]=mapped_column(String(2000), default='')
    status: Mapped[str]=mapped_column(String(30), default='draft')

class Publication(Base):
    __tablename__='publications'
    id: Mapped[int]=mapped_column(primary_key=True)
    campaign_id: Mapped[int]=mapped_column(ForeignKey('content_campaigns.id'), index=True)
    variant_id: Mapped[int]=mapped_column(ForeignKey('content_variants.id'), index=True)
    platform: Mapped[str]=mapped_column(String(30), index=True)
    status: Mapped[str]=mapped_column(String(30), default='pending')
    scheduled_at: Mapped[datetime|None]=mapped_column(DateTime, nullable=True)
    published_at: Mapped[datetime|None]=mapped_column(DateTime, nullable=True)
    external_post_id: Mapped[str]=mapped_column(String(300), default='')
    external_post_url: Mapped[str]=mapped_column(String(2000), default='')
    error_message: Mapped[str]=mapped_column(Text, default='')
    retry_count: Mapped[int]=mapped_column(Integer, default=0)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)
