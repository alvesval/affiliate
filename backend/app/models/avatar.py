from datetime import datetime
from sqlalchemy import ForeignKey, LargeBinary, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.core.db import Base

class UserAvatar(Base):
    __tablename__ = 'user_avatars'
    user_id: Mapped[int] = mapped_column(ForeignKey('saas_users.id'), primary_key=True)
    content: Mapped[bytes] = mapped_column(LargeBinary)
    version: Mapped[str] = mapped_column(String(64))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
