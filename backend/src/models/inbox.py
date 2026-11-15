from sqlalchemy import String, Double, Boolean, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column
from src.config.database import Base
class InboxItem(Base):
    """演示收件端的入件记录。dispatch_id 为幂等键:同一投递号不重复入件。"""
    __tablename__ = 'inbox_items'
    id: Mapped[int] = mapped_column(primary_key=True)
    dispatch_id: Mapped[int] = mapped_column(Integer, unique=True)
    delivery_id: Mapped[int] = mapped_column(Integer)
    recipient: Mapped[str] = mapped_column(String(120), default='')
    checksum: Mapped[str] = mapped_column(String(64))
    filename: Mapped[str] = mapped_column(String(160))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    received_at: Mapped[float] = mapped_column(Double)
    duplicates: Mapped[int] = mapped_column(Integer, default=0)  # 重复投递被拦截次数
class ReceiverState(Base):
    """演示收件端开关:模拟回执通道故障(入件正常,回执与查询丢失)。"""
    __tablename__ = 'receiver_state'
    id: Mapped[int] = mapped_column(primary_key=True)
    drop_receipts: Mapped[bool] = mapped_column(Boolean, default=False)
