from sqlalchemy import String, Double, ForeignKey, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column
from src.config.database import Base
class Dispatch(Base):
    """按收件方确认的投递。地址在创建时快照:收件地址修改只影响之后的新投递,重发旧件仍到原地址。"""
    __tablename__ = 'dispatches'
    id: Mapped[int] = mapped_column(primary_key=True)
    delivery_id: Mapped[int] = mapped_column(ForeignKey('deliveries.id'))
    recipient_id: Mapped[int] = mapped_column(ForeignKey('recipients.id'))
    recipient_name: Mapped[str] = mapped_column(String(120))
    address: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(16), default='pending')  # pending待发/sent待确认/delivered已送达/failed失败/revoked已撤销
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    sent_at: Mapped[float | None] = mapped_column(Double, nullable=True)  # 最近一次报文可能已到达对方的时间
    next_attempt_at: Mapped[float] = mapped_column(Double, default=0)
    receipt_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    receipt_at: Mapped[float | None] = mapped_column(Double, nullable=True)
    receipt_late: Mapped[bool] = mapped_column(Boolean, default=False)  # 撤销后登记到的迟到回执
    revoked_at: Mapped[float | None] = mapped_column(Double, nullable=True)
    last_error: Mapped[str] = mapped_column(String(300), default='')
    created_at: Mapped[float] = mapped_column(Double)
    updated_at: Mapped[float] = mapped_column(Double)
class DispatchAttempt(Base):
    """每次投递/查询/撤销动作留痕,供页面逐条核对。"""
    __tablename__ = 'dispatch_attempts'
    id: Mapped[int] = mapped_column(primary_key=True)
    dispatch_id: Mapped[int] = mapped_column(ForeignKey('dispatches.id'))
    at: Mapped[float] = mapped_column(Double)
    kind: Mapped[str] = mapped_column(String(16))  # create/send/query/retry/revoke
    result: Mapped[str] = mapped_column(String(24))  # created/ok/duplicate/missing/error/receipt_lost/refused/failed/retry/revoked/revoke_rejected/late_receipt
    detail: Mapped[str] = mapped_column(String(300), default='')
