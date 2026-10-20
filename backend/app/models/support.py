"""Support conversations isolated by workspace; notes are staff-only."""
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Boolean, Integer, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base

class SupportTicket(Base):
    __tablename__ = 'support_tickets'
    __table_args__ = (Index('ix_support_company_status_updated','company_id','status','updated_at'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey('companies.id'), index=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey('saas_users.id'))
    campaign_id: Mapped[int | None] = mapped_column(ForeignKey('content_campaigns.id'), nullable=True)
    subject: Mapped[str] = mapped_column(String(180))
    category: Mapped[str] = mapped_column(String(40))
    priority: Mapped[str] = mapped_column(String(20), default='normal')
    status: Mapped[str] = mapped_column(String(30), default='open', index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

class SupportMessage(Base):
    __tablename__ = 'support_messages'
    __table_args__ = (Index('ix_support_message_ticket_id','ticket_id','id'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey('support_tickets.id'), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey('saas_users.id'))
    author_is_staff: Mapped[bool] = mapped_column(Boolean, default=False)
    internal: Mapped[bool] = mapped_column(Boolean, default=False)
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class SupportRead(Base):
    __tablename__ = 'support_reads'
    __table_args__ = (UniqueConstraint('ticket_id','user_id',name='uq_support_ticket_reader'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey('support_tickets.id'))
    user_id: Mapped[int] = mapped_column(ForeignKey('saas_users.id'))
    last_message_id: Mapped[int] = mapped_column(Integer, default=0)
