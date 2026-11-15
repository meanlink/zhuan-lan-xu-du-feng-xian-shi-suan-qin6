import hashlib, json
def checksum(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
def dataset_dict(d):
    return {'id':d.id, 'name':d.name, 'source':d.source, 'rows':len(d.records), 'checksum':d.checksum, 'created_at':d.created_at}
def job_dict(j):
    return {k:getattr(j,k) for k in ['id','name','dataset_id','params','status','result','error','approved','created_at','finished_at']}
def report_dict(r):
    return {k:getattr(r,k) for k in ['id','name','job_id','destination','interval_seconds','next_run','enabled']}
def delivery_dict(d):
    return {k:getattr(d,k) for k in ['id','report_id','created_at','checksum','filename','destination']}
def recipient_dict(r):
    return {k:getattr(r,k) for k in ['id','name','address','enabled','created_at','updated_at']}
def dispatch_dict(d):
    return {k:getattr(d,k) for k in ['id','delivery_id','recipient_id','recipient_name','address','status','attempts','sent_at','next_attempt_at','receipt_id','receipt_at','receipt_late','revoked_at','last_error','created_at','updated_at']}
def attempt_dict(a):
    return {k:getattr(a,k) for k in ['id','dispatch_id','at','kind','result','detail']}
def inbox_dict(i):
    return {k:getattr(i,k) for k in ['id','dispatch_id','delivery_id','recipient','checksum','filename','received_at','duplicates']}
