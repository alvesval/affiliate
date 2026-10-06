from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base

class SocialConnection(Base):
    __table_args__=(UniqueConstraint('company_id','platform',name='uq_social_connection_company_platform'),)
    company_id: Mapped[int|None]=mapped_column(Integer, nullable=True, index=True)
    __tablename__='social_connections'
    id: Mapped[int]=mapped_column(primary_key=True)
    platform: Mapped[str]=mapped_column(String(30), index=True)
    account_name: Mapped[str]=mapped_column(String(180), default='')
    external_user_id: Mapped[str]=mapped_column(String(180), default='')
    access_token_enc: Mapped[str]=mapped_column(Text, default='')
    refresh_token_enc: Mapped[str]=mapped_column(Text, default='')
    scopes: Mapped[str]=mapped_column(Text, default='')
    expires_at: Mapped[datetime|None]=mapped_column(DateTime, nullable=True)
    connected_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class SocialOAuthAttempt(Base):
    company_id: Mapped[int|None]=mapped_column(Integer, nullable=True, index=True)
    __tablename__='social_oauth_attempts'
    id: Mapped[int]=mapped_column(primary_key=True)
    platform: Mapped[str]=mapped_column(String(30), index=True)
    state: Mapped[str]=mapped_column(String(180), unique=True, index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class ContentCampaign(Base):
    company_id: Mapped[int|None]=mapped_column(Integer, nullable=True, index=True)
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
    company_id: Mapped[int|None]=mapped_column(Integer, nullable=True, index=True)
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
    media_storage_key: Mapped[str]=mapped_column(String(1000), default='')
    media_filename: Mapped[str]=mapped_column(String(500), default='')
    media_content_type: Mapped[str]=mapped_column(String(100), default='')
    media_size: Mapped[int]=mapped_column(Integer, default=0)
    media_duration_seconds: Mapped[int]=mapped_column(Integer, default=0)
    affiliate_url: Mapped[str]=mapped_column(String(1000), default='')
    affiliate_label: Mapped[str]=mapped_column(String(120), default='')
    link_placement: Mapped[str]=mapped_column(String(40), default='bio')
    affiliate_configured_at: Mapped[datetime|None]=mapped_column(DateTime, nullable=True)
    status: Mapped[str]=mapped_column(String(30), default='draft')

class Publication(Base):
    company_id: Mapped[int|None]=mapped_column(Integer, nullable=True, index=True)
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
    privacy_level: Mapped[str]=mapped_column(String(50), default='SELF_ONLY')
    disable_comment: Mapped[bool]=mapped_column(Boolean, default=False)
    disable_duet: Mapped[bool]=mapped_column(Boolean, default=False)
    disable_stitch: Mapped[bool]=mapped_column(Boolean, default=False)
    user_consent: Mapped[bool]=mapped_column(Boolean, default=False)
    brand_content_toggle: Mapped[bool]=mapped_column(Boolean, default=False)
    brand_organic_toggle: Mapped[bool]=mapped_column(Boolean, default=False)
    is_aigc: Mapped[bool]=mapped_column(Boolean, default=False)
    tiktok_status: Mapped[str]=mapped_column(String(80), default='')
    tiktok_fail_reason: Mapped[str]=mapped_column(Text, default='')
    uploaded_bytes: Mapped[int]=mapped_column(Integer, default=0)
    public_post_ids: Mapped[str]=mapped_column(Text, default='')
    pinterest_board_id: Mapped[str]=mapped_column(String(180), default='')
    pinterest_board_name: Mapped[str]=mapped_column(String(300), default='')
    pinterest_cover_url: Mapped[str]=mapped_column(String(2000), default='')
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class ProductVisualReference(Base):
    """Auditable real-product reference used by the creative/video pipeline."""
    __tablename__='product_visual_references'
    id: Mapped[int]=mapped_column(primary_key=True)
    company_id: Mapped[int]=mapped_column(Integer,index=True)
    campaign_id: Mapped[int]=mapped_column(ForeignKey('content_campaigns.id'),index=True)
    product_id: Mapped[int]=mapped_column(ForeignKey('products.id'),index=True)
    storage_key: Mapped[str]=mapped_column(String(1000),default='')
    filename: Mapped[str]=mapped_column(String(500),default='')
    content_type: Mapped[str]=mapped_column(String(100),default='')
    size_bytes: Mapped[int]=mapped_column(Integer,default=0)
    width: Mapped[int]=mapped_column(Integer,default=0)
    height: Mapped[int]=mapped_column(Integer,default=0)
    sha256: Mapped[str]=mapped_column(String(64),default='',index=True)
    source_type: Mapped[str]=mapped_column(String(40),default='upload')
    source_url: Mapped[str]=mapped_column(String(2000),default='')
    is_primary: Mapped[bool]=mapped_column(Boolean,default=False)
    position: Mapped[int]=mapped_column(Integer,default=1)
    validated_at: Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
