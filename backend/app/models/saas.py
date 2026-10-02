from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Integer, Boolean, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base

class Company(Base):
    __tablename__='companies'
    id: Mapped[int]=mapped_column(primary_key=True)
    name: Mapped[str]=mapped_column(String(180), index=True)
    slug: Mapped[str]=mapped_column(String(120), unique=True, index=True)
    status: Mapped[str]=mapped_column(String(30), default='trial')
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class SaaSUser(Base):
    __tablename__='saas_users'
    id: Mapped[int]=mapped_column(primary_key=True)
    email: Mapped[str]=mapped_column(String(180), unique=True, index=True)
    name: Mapped[str]=mapped_column(String(140))
    password_hash: Mapped[str]=mapped_column(String(255))
    is_active: Mapped[bool]=mapped_column(Boolean, default=True)
    is_super_admin: Mapped[bool]=mapped_column(Boolean, default=False)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)
    last_login_at: Mapped[datetime|None]=mapped_column(DateTime, nullable=True)

class CompanyMember(Base):
    __tablename__='company_members'
    __table_args__=(UniqueConstraint('company_id','user_id',name='uq_company_member'),)
    id: Mapped[int]=mapped_column(primary_key=True)
    company_id: Mapped[int]=mapped_column(ForeignKey('companies.id'), index=True)
    user_id: Mapped[int]=mapped_column(ForeignKey('saas_users.id'), index=True)
    role: Mapped[str]=mapped_column(String(30), default='VIEWER')
    status: Mapped[str]=mapped_column(String(30), default='active')
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class Plan(Base):
    __tablename__='plans'
    id: Mapped[int]=mapped_column(primary_key=True)
    code: Mapped[str]=mapped_column(String(40), unique=True, index=True)
    name: Mapped[str]=mapped_column(String(80))
    active: Mapped[bool]=mapped_column(Boolean, default=True)
    monthly_price_cents: Mapped[int]=mapped_column(Integer, default=0)
    currency: Mapped[str]=mapped_column(String(10), default='BRL')
    limits_json: Mapped[str]=mapped_column(Text, default='{}')

class Subscription(Base):
    __tablename__='subscriptions'
    id: Mapped[int]=mapped_column(primary_key=True)
    company_id: Mapped[int]=mapped_column(ForeignKey('companies.id'), unique=True, index=True)
    plan_code: Mapped[str]=mapped_column(String(40), default='TRIAL')
    status: Mapped[str]=mapped_column(String(30), default='trialing')
    provider: Mapped[str]=mapped_column(String(30), default='manual')
    provider_customer_id: Mapped[str]=mapped_column(String(180), default='')
    provider_subscription_id: Mapped[str]=mapped_column(String(180), default='')
    trial_ends_at: Mapped[datetime|None]=mapped_column(DateTime, nullable=True)
    current_period_end: Mapped[datetime|None]=mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class AuditEvent(Base):
    __tablename__='audit_events'
    id: Mapped[int]=mapped_column(primary_key=True)
    company_id: Mapped[int|None]=mapped_column(ForeignKey('companies.id'), nullable=True, index=True)
    user_id: Mapped[int|None]=mapped_column(ForeignKey('saas_users.id'), nullable=True, index=True)
    action: Mapped[str]=mapped_column(String(120), index=True)
    entity_type: Mapped[str]=mapped_column(String(80), default='')
    entity_id: Mapped[str]=mapped_column(String(80), default='')
    detail_json: Mapped[str]=mapped_column(Text, default='{}')
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class ContentAutomationProfile(Base):
    __tablename__='content_automation_profiles'
    id: Mapped[int]=mapped_column(primary_key=True)
    company_id: Mapped[int]=mapped_column(ForeignKey('companies.id'), index=True)
    name: Mapped[str]=mapped_column(String(120), default='Autopilot padrão')
    enabled: Mapped[bool]=mapped_column(Boolean, default=False)
    platforms_csv: Mapped[str]=mapped_column(String(300), default='TikTok,Instagram')
    tone: Mapped[str]=mapped_column(String(80), default='Direto e acessível')
    audience: Mapped[str]=mapped_column(String(200), default='')
    duration_seconds: Mapped[int]=mapped_column(Integer, default=30)
    daily_limit: Mapped[int]=mapped_column(Integer, default=3)
    require_human_approval: Mapped[bool]=mapped_column(Boolean, default=True)
    min_opportunity_score: Mapped[int]=mapped_column(Integer, default=60)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)
