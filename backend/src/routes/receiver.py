from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from src.config.database import get_db
from src.config.settings import RECEIVER_TOKEN
from src.services import inbox
router = APIRouter()
class Incoming(BaseModel):
    dispatch_id: int
    delivery_id: int
    recipient: str = Field(default='', max_length=120)
    filename: str = Field(min_length=1, max_length=160)
    checksum: str = Field(min_length=64, max_length=64)
    csv_b64: str = Field(min_length=1)
    snapshot: dict = {}
def token_guard(x_inbox_token: str | None = Header(None)):
    if x_inbox_token != RECEIVER_TOKEN:
        raise HTTPException(401, '收件端令牌无效')
@router.post('/receiver/inbox', dependencies=[Depends(token_guard)])
def receive(body: Incoming, db=Depends(get_db)):
    """演示收件端:归档入件并返回回执。故障模式下照常入件,但回执丢失(503)。"""
    state = inbox.get_state(db)
    receipt = inbox.receive(db, body.model_dump())
    db.commit()
    if state and state.drop_receipts:
        raise HTTPException(503, '回执通道故障(演示):已入件但回执丢失')
    return receipt
@router.get('/receiver/inbox/{dispatch_id}', dependencies=[Depends(token_guard)])
def query(dispatch_id: int, db=Depends(get_db)):
    """查接收结果:发送方重试前以此确认投递号是否已入件。故障模式下查询同样丢失(503)。"""
    state = inbox.get_state(db)
    if state and state.drop_receipts:
        raise HTTPException(503, '查询通道故障(演示)')
    receipt = inbox.query(db, dispatch_id)
    if not receipt:
        raise HTTPException(404, '该投递号未入件')
    return receipt
