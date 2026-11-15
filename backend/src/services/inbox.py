import time, base64, hashlib, binascii
from fastapi import HTTPException
from sqlalchemy import select
from src.models import InboxItem, ReceiverState
def get_state(db):
    return db.get(ReceiverState, 1)
def set_drop(db, drop):
    s = db.get(ReceiverState, 1)
    if not s:
        s = ReceiverState(id=1, drop_receipts=drop)
        db.add(s)
    else:
        s.drop_receipts = drop
    db.flush()
    return s
def receive(db, body):
    """收件端入件:校验归档完整性;同一投递号幂等,重复投递只登记拦截、不重复入件。"""
    try:
        raw = base64.b64decode(body['csv_b64'], validate=True)
    except (binascii.Error, ValueError):
        raise HTTPException(422, '投递内容编码无效')
    if hashlib.sha256(raw).hexdigest() != body['checksum']:
        raise HTTPException(422, '校验和不符,拒绝入件')
    existing = db.scalar(select(InboxItem).where(InboxItem.dispatch_id == body['dispatch_id']))
    if existing:
        existing.duplicates += 1
        db.flush()
        return {'inbox_id': existing.id, 'received_at': existing.received_at, 'duplicate': True}
    item = InboxItem(dispatch_id=body['dispatch_id'], delivery_id=body['delivery_id'],
                     recipient=body.get('recipient', ''), checksum=body['checksum'],
                     filename=body['filename'],
                     payload={'snapshot': body.get('snapshot'), 'csv_b64': body['csv_b64']},
                     received_at=time.time())
    db.add(item); db.flush()
    return {'inbox_id': item.id, 'received_at': item.received_at, 'duplicate': False}
def query(db, dispatch_id):
    """查接收结果:发送方重试前以此确认投递号是否已入件。"""
    item = db.scalar(select(InboxItem).where(InboxItem.dispatch_id == dispatch_id))
    if not item:
        return None
    return {'inbox_id': item.id, 'received_at': item.received_at, 'duplicate': False}
