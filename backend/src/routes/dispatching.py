import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from src.config.database import get_db
from src.models import Recipient, Dispatch, DispatchAttempt, Delivery, InboxItem
from src.schemas.recipient import RecipientInput, RecipientUpdate, RedispatchInput, InboxModeInput
from src.middlewares.auth import current_user, admin_only
from src.services import dispatching as svc
from src.services import inbox as inbox_svc
from src.services.audit import record
from src.utils.serialization import recipient_dict, dispatch_dict, attempt_dict, inbox_dict
router = APIRouter()
@router.get('/recipients')
def recipients(db=Depends(get_db), u=Depends(current_user)):
    return [recipient_dict(r) for r in db.scalars(select(Recipient).order_by(Recipient.id))]
@router.post('/recipients', status_code=201)
def create_recipient(data: RecipientInput, db=Depends(get_db), u=Depends(admin_only)):
    now = time.time()
    r = Recipient(name=data.name, address=data.address, enabled=True, created_at=now, updated_at=now)
    db.add(r); db.flush()
    record(db, u.email, 'recipient.create', {'id': r.id, 'address': r.address})
    db.commit()
    return recipient_dict(r)
@router.patch('/recipients/{id}')
def update_recipient(id: int, data: RecipientUpdate, db=Depends(get_db), u=Depends(admin_only)):
    r = db.get(Recipient, id)
    if not r: raise HTTPException(404, '收件方不存在')
    changes = {}
    if data.name is not None: r.name = data.name; changes['name'] = data.name
    if data.address is not None: r.address = data.address; changes['address'] = data.address  # 只影响之后的新投递;旧投递仍按快照地址
    if data.enabled is not None: r.enabled = data.enabled; changes['enabled'] = data.enabled
    r.updated_at = time.time()
    record(db, u.email, 'recipient.update', {'id': id, **changes})
    db.commit()
    return recipient_dict(r)
def _with_delivery(db, d):
    delivery = db.get(Delivery, d.delivery_id)
    return {**dispatch_dict(d),
            'filename': delivery.filename if delivery else '',
            'checksum': delivery.checksum if delivery else ''}
@router.get('/dispatches')
def dispatches(delivery_id: int | None = None, db=Depends(get_db), u=Depends(current_user)):
    q = select(Dispatch).order_by(Dispatch.id.desc()).limit(200)
    if delivery_id: q = select(Dispatch).where(Dispatch.delivery_id == delivery_id).order_by(Dispatch.id.desc()).limit(200)
    return [_with_delivery(db, d) for d in db.scalars(q)]
@router.get('/dispatches/{id}')
def dispatch_detail(id: int, db=Depends(get_db), u=Depends(current_user)):
    d = db.get(Dispatch, id)
    if not d: raise HTTPException(404, '投递不存在')
    attempts = [attempt_dict(a) for a in db.scalars(select(DispatchAttempt).where(DispatchAttempt.dispatch_id == id).order_by(DispatchAttempt.id))]
    return {**_with_delivery(db, d), 'attempts_log': attempts}
@router.post('/dispatches/{id}/retry')
def retry(id: int, db=Depends(get_db), u=Depends(admin_only)):
    d = db.get(Dispatch, id)
    if not d: raise HTTPException(404, '投递不存在')
    svc.retry(db, d)
    record(db, u.email, 'dispatch.retry', {'id': id})
    db.commit()
    return dispatch_dict(d)
@router.post('/dispatches/{id}/revoke')
def revoke(id: int, db=Depends(get_db), u=Depends(admin_only)):
    d = db.get(Dispatch, id)
    if not d: raise HTTPException(404, '投递不存在')
    try:
        svc.revoke(db, d)
        record(db, u.email, 'dispatch.revoke', {'id': id, 'recipient': d.recipient_name})
    except HTTPException as e:
        record(db, u.email, 'dispatch.revoke.rejected', {'id': id, 'detail': str(e.detail)})
        db.commit()  # 撤销尝试与对账结果同样留痕
        raise
    db.commit()
    return dispatch_dict(d)
@router.post('/deliveries/{id}/dispatches', status_code=201)
def redispatch(id: int, data: RedispatchInput, db=Depends(get_db), u=Depends(admin_only)):
    delivery = db.get(Delivery, id)
    if not delivery: raise HTTPException(404, '归档不存在')
    recipient = db.get(Recipient, data.recipient_id)
    if not recipient: raise HTTPException(404, '收件方不存在')
    d = svc.dispatch_to(db, delivery, recipient)
    record(db, u.email, 'dispatch.redispatch', {'delivery': id, 'dispatch': d.id, 'recipient': recipient.name})
    db.commit()
    return dispatch_dict(d)
@router.get('/inbox')
def inbox_view(db=Depends(get_db), u=Depends(current_user)):
    state = inbox_svc.get_state(db)
    items = [inbox_dict(i) for i in db.scalars(select(InboxItem).order_by(InboxItem.id.desc()).limit(100))]
    return {'drop_receipts': bool(state and state.drop_receipts), 'items': items}
@router.post('/inbox/mode')
def inbox_mode(data: InboxModeInput, db=Depends(get_db), u=Depends(admin_only)):
    s = inbox_svc.set_drop(db, data.drop_receipts)
    record(db, u.email, 'inbox.mode', {'drop_receipts': s.drop_receipts})
    db.commit()
    return {'drop_receipts': s.drop_receipts}
