import time, os, json, base64, logging
from fastapi import HTTPException
from sqlalchemy import select
from src.models import Recipient, Dispatch, DispatchAttempt, Delivery
from src.config.settings import ARTIFACT_DIR, RECEIVER_TOKEN
from src.utils.http import call
MAX_ATTEMPTS = 12      # 单个投递号的最大尝试次数,超出转为失败,待人工重试
RECONCILE_SECONDS = 20 # 已撤销但可能已送达的投递,迟到回执对账间隔
def create_dispatches(db, delivery):
    """归档内容固定后,为每个启用中的收件方生成独立投递,快照当前收件地址。"""
    now = time.time()
    for r in db.scalars(select(Recipient).where(Recipient.enabled == True)):
        d = Dispatch(delivery_id=delivery.id, recipient_id=r.id, recipient_name=r.name,
                     address=r.address, status='pending', next_attempt_at=now,
                     created_at=now, updated_at=now)
        db.add(d); db.flush()
        log_attempt(db, d, 'create', 'created', '归档已固定,快照地址 ' + r.address)
def log_attempt(db, d, kind, result, detail=''):
    db.add(DispatchAttempt(dispatch_id=d.id, at=time.time(), kind=kind, result=result, detail=detail[:290]))
def backoff(attempts):
    return min(5 * 2 ** min(attempts, 4), 90)
def record_receipt(db, d, receipt):
    """登记回执。与撤销相撞时保留已接收事实:状态转为已送达,撤销时间保留可查。"""
    d.status = 'delivered'
    d.receipt_id = str(receipt.get('inbox_id'))
    d.receipt_at = float(receipt.get('received_at') or time.time())
    d.receipt_late = bool(d.revoked_at)
    d.last_error = ''
    d.updated_at = time.time()
def load_payload(d, delivery):
    """读取固定下来的归档文件构造报文,发送内容以归档为准,不重新计算。"""
    base = os.path.join(ARTIFACT_DIR, delivery.filename)
    with open(base, 'rb') as f:
        csv_b64 = base64.b64encode(f.read()).decode()
    with open(base + '.json') as f:
        snapshot = json.load(f)
    return {'dispatch_id': d.id, 'delivery_id': delivery.id, 'recipient': d.recipient_name,
            'filename': delivery.filename, 'checksum': delivery.checksum,
            'csv_b64': csv_b64, 'snapshot': snapshot}
def query(db, d, count=True):
    """先查接收结果:对方已入件则直接登记回执,不重复入件。返回 True已入件/False未入件/None不确定。"""
    if count: d.attempts += 1
    status, payload, err = call('GET', d.address.rstrip('/') + '/' + str(d.id), token=RECEIVER_TOKEN)
    if status == 200 and payload and payload.get('inbox_id') is not None:
        late = bool(d.revoked_at)
        record_receipt(db, d, payload)
        log_attempt(db, d, 'query', 'late_receipt' if late else 'ok',
                    ('撤销后登记到迟到回执 ' if late else '对方已入件,登记回执 ') + str(d.receipt_id))
        return True
    if status == 404:
        log_attempt(db, d, 'query', 'missing', '对方未入件')
        return False
    log_attempt(db, d, 'query', 'error', '查询失败: ' + (err or 'HTTP ' + str(status)))
    return None
def send(db, d, delivery):
    """按投递号快照地址发送。拿不到回执一律转待确认,下一轮先查接收结果再决定是否补发。"""
    d.attempts += 1
    status, payload, err = call('POST', d.address, load_payload(d, delivery), token=RECEIVER_TOKEN)
    now = time.time()
    if status in (200, 201) and payload and payload.get('inbox_id') is not None:
        record_receipt(db, d, payload)
        log_attempt(db, d, 'send', 'duplicate' if payload.get('duplicate') else 'ok', '回执 ' + str(d.receipt_id))
    elif status is not None and 400 <= status < 500 and status not in (408, 429):
        d.status = 'failed'
        d.last_error = ('对方拒收 HTTP ' + str(status) + ' ' + str((payload or {}).get('detail', '')))[:290]
        log_attempt(db, d, 'send', 'refused', d.last_error)
    else:
        d.sent_at = now  # 保守标记报文可能已到达(回执丢失),供撤销后的迟到回执对账
        d.status = 'sent'
        d.last_error = (err or 'HTTP ' + str(status))[:290]
        log_attempt(db, d, 'send', 'receipt_lost', '未拿到回执,转待确认: ' + d.last_error)
    d.next_attempt_at = now + backoff(d.attempts)
    d.updated_at = now
def _advance(db, d, now):
    if d.attempts >= MAX_ATTEMPTS:
        d.status = 'failed'; d.last_error = '尝试次数用尽,待人工重试'
        log_attempt(db, d, 'send', 'failed', d.last_error)
        d.updated_at = now
        return
    delivery = db.get(Delivery, d.delivery_id)
    if not delivery:
        d.status = 'failed'; d.last_error = '归档不存在'
        log_attempt(db, d, 'send', 'failed', d.last_error)
        d.updated_at = now
        return
    if d.status == 'sent' or d.sent_at:
        known = query(db, d)
        if known is True: return
        if known is None:
            d.next_attempt_at = now + backoff(d.attempts)
            d.updated_at = now
            return
    send(db, d, delivery)
def run_cycle(db):
    """worker 周期:推进待发/待确认投递;对已撤销但可能已送达的只做查询对账,不补发。
    全部状态落在数据库,worker 中断重启后本周期自然续跑;单个投递异常不影响其他投递。"""
    now = time.time()
    due = list(db.scalars(select(Dispatch).where(Dispatch.status.in_(['pending', 'sent']),
                                                 Dispatch.next_attempt_at <= now).limit(20)))
    for d in due:
        try:
            _advance(db, d, now)
        except Exception as e:
            logging.exception('Dispatch %s advance failed', d.id)
            d.last_error = ('内部错误: ' + str(e))[:290]
            d.next_attempt_at = now + backoff(d.attempts)
            d.updated_at = now
    for d in db.scalars(select(Dispatch).where(Dispatch.status == 'revoked',
                                               Dispatch.sent_at.isnot(None),
                                               Dispatch.next_attempt_at <= now).limit(10)):
        try:
            query(db, d, count=False)  # 迟到回执可对账,且不触发重发
        except Exception:
            logging.exception('Dispatch %s reconcile failed', d.id)
        d.next_attempt_at = now + RECONCILE_SECONDS
        d.updated_at = now
def retry(db, d):
    """人工重试:沿用原投递号,重置尝试预算(历史在尝试记录中保留),发送前仍会先查接收结果。"""
    if d.status in ('delivered', 'revoked'):
        raise HTTPException(409, '已送达或已撤销的投递不能重试')
    d.status = 'pending'
    d.attempts = 0
    d.last_error = ''
    d.next_attempt_at = time.time()
    d.updated_at = time.time()
    log_attempt(db, d, 'retry', 'retry', '人工重试,沿用原投递号 ' + str(d.id))
def revoke(db, d):
    """撤销:先查接收结果。已接收的保留已接收事实并拒绝撤销;未接收的停止发送。"""
    now = time.time()
    if d.status == 'delivered':
        log_attempt(db, d, 'revoke', 'revoke_rejected', '对方已接收,撤销未执行')
        raise HTTPException(409, '对方已确认接收,撤销未执行;已接收事实保留')
    if d.status == 'revoked':
        raise HTTPException(409, '该投递已处于撤销状态')
    if d.sent_at:
        if query(db, d, count=False) is True:
            d.revoked_at = now
            d.updated_at = now
            log_attempt(db, d, 'revoke', 'revoke_rejected', '撤销时确认对方已接收,保留已接收事实')
            raise HTTPException(409, '对方已接收,撤销未生效;已接收事实保留')
    d.status = 'revoked'
    d.revoked_at = now
    d.last_error = ''
    if d.sent_at: d.next_attempt_at = now + RECONCILE_SECONDS
    d.updated_at = now
    log_attempt(db, d, 'revoke', 'revoked', '停止发送' + (',等待迟到回执对账' if d.sent_at else ''))
def dispatch_to(db, delivery, recipient):
    """把既有归档补投给收件方:生成新投递号,快照当前地址;旧投递号仍按原地址。"""
    existing = list(db.scalars(select(Dispatch).where(Dispatch.delivery_id == delivery.id,
                                                      Dispatch.recipient_id == recipient.id)))
    if any(d.status in ('pending', 'sent') for d in existing):
        raise HTTPException(409, '该收件方已有进行中的投递')
    if any(d.status == 'delivered' for d in existing):
        raise HTTPException(409, '该收件方已接收此归档')
    if any(d.status == 'failed' for d in existing):
        raise HTTPException(409, '存在失败的投递,请使用重试以沿用原投递号')
    now = time.time()
    d = Dispatch(delivery_id=delivery.id, recipient_id=recipient.id, recipient_name=recipient.name,
                 address=recipient.address, status='pending', next_attempt_at=now,
                 created_at=now, updated_at=now)
    db.add(d); db.flush()
    log_attempt(db, d, 'create', 'created', '补投创建,快照地址 ' + recipient.address)
    return d
