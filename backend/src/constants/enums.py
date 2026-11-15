from enum import Enum
class Role(str, Enum):
    admin = 'admin'
    analyst = 'analyst'
    viewer = 'viewer'
class JobStatus(str, Enum):
    queued = 'queued'
    running = 'running'
    completed = 'completed'
    failed = 'failed'
class DispatchStatus(str, Enum):
    pending = 'pending'      # 待发
    sent = 'sent'            # 待确认:报文已发出但回执未拿到
    delivered = 'delivered'  # 已送达:回执已登记
    failed = 'failed'        # 失败:对方拒收或尝试次数用尽
    revoked = 'revoked'      # 已撤销:尚未接收,停止发送
