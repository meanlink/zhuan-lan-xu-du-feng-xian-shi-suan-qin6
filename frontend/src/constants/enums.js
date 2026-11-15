export const Role={admin:'业务负责人',analyst:'分析员',viewer:'观察员'};
export const JobStatus={queued:'排队中',running:'计算中',completed:'已完成',failed:'执行失败'};
export const DispatchStatus={pending:'待发',sent:'待确认',delivered:'已送达',failed:'失败',revoked:'已撤销'};
export const AttemptKind={create:'创建',send:'投递',query:'查询',retry:'重试',revoke:'撤销'};
export const AttemptResult={created:'已创建',ok:'成功',duplicate:'重复拦截',missing:'未入件',error:'错误',receipt_lost:'回执丢失',refused:'对方拒收',failed:'转为失败',retry:'重新排队',revoked:'已撤销',revoke_rejected:'撤销被拒',late_receipt:'迟到回执'};
