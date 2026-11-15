from sqlalchemy import String, Double, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from src.config.database import Base
class Recipient(Base):
    __tablename__ = 'recipients'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    address: Mapped[str] = mapped_column(String(300))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[float] = mapped_column(Double)
    updated_at: Mapped[float] = mapped_column(Double)
