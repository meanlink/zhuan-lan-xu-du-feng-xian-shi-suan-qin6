import {recipients,dispatches,inbox,reports} from '../api/entities.js';
import {session} from '../stores/session.js';
import {heading} from '../components/common/shell.js';
import {esc,date,notify} from '../utils/dom.js';
import {submit} from '../hooks/forms.js';
import {DispatchStatus,AttemptKind,AttemptResult} from '../constants/enums.js';
import {route} from '../router/index.js';
const admin=()=>session.user.role==='admin';
const badge=s=>'<span class="status st-'+esc(s)+'">'+esc(DispatchStatus[s]||s)+'</span>';
const receipt=d=>d.receipt_id?('#'+esc(d.receipt_id)+' · '+date(d.receipt_at)+(d.receipt_late?' <em class="late-tag">迟到回执</em>':'')):'—';
const row=d=>'<tr><td>#'+d.id+'</td><td>'+esc(d.filename||'—')+'</td><td>'+esc(d.recipient_name)+'</td><td class="addr">'+esc(d.address)+'</td><td>'+badge(d.status)+'</td><td>'+d.attempts+'</td><td>'+receipt(d)+'</td><td>'+(d.revoked_at?date(d.revoked_at):'—')+'</td><td class="ops"><button class="text-button" data-detail="'+d.id+'">核对</button>'+(admin()&&(d.status==='sent'||d.status==='failed')?'<button class="text-button" data-retry="'+d.id+'">重试</button>':'')+(admin()&&['pending','sent','failed'].includes(d.status)?'<button class="text-button" data-revoke="'+d.id+'">撤销</button>':'')+'</td></tr>';
export async function dispatchPage(){
 const [rcps,ds,box,deliveries]=await Promise.all([recipients.list(),dispatches.list(),inbox.view(),reports.deliveries()]);
 const canAdmin=admin();
 const ledger='<section class="panel"><div class="section-title"><h2>投递台账</h2><span>'+ds.length+' 条投递 · 各收件方独立记录</span></div>'
  +(canAdmin?'<form id="redispatch-form" class="inline-form"><label>归档<select name="delivery_id">'+deliveries.map(d=>'<option value="'+d.id+'">'+esc(d.filename)+'</option>').join('')+'</select></label><label>收件方<select name="recipient_id">'+rcps.map(r=>'<option value="'+r.id+'">'+esc(r.name)+'</option>').join('')+'</select></label><button type="submit" class="button small" '+(!deliveries.length||!rcps.length?'disabled':'')+'>补投</button></form>':'')
  +'<p class="hint">归档固定后才发送;重发沿用原投递号并先查接收结果,不重复入件;补投生成新投递号并快照当前地址。</p>'
  +(ds.length?'<div class="table-wrap"><table><thead><tr><th>投递号</th><th>归档</th><th>收件方</th><th>投递地址(快照)</th><th>状态</th><th>尝试</th><th>回执</th><th>撤销于</th><th>操作</th></tr></thead><tbody>'+ds.map(row).join('')+'</tbody></table></div>':'<p class="empty">暂无投递。归档计划执行或补投后,各收件方的投递会出现在此处。</p>')
  +'<div id="dispatch-detail"></div></section>';
 const recipientsPanel='<section class="panel"><div class="section-title"><h2>收件方</h2><span>'+rcps.filter(r=>r.enabled).length+' 个启用中</span></div>'
  +'<div class="schedule-list">'+rcps.map(r=>'<article><div><strong>'+esc(r.name)+'</strong><p class="addr">'+esc(r.address)+'</p><small>'+(r.enabled?'启用中':'已停用')+' · 更新于 '+date(r.updated_at)+'</small></div>'+(canAdmin?'<button class="button small" data-edit="'+r.id+'" data-name="'+esc(r.name)+'" data-address="'+esc(r.address)+'" data-enabled="'+(r.enabled?1:0)+'">修改</button>':'')+'</article>').join('')+'</div>'
  +(canAdmin?'<form id="recipient-form"><label>名称<input name="name" required minlength="2" placeholder="新刊编辑部"></label><label>收件地址<input name="address" required value="http://backend:8000/receiver/inbox"></label><button type="submit" class="primary">添加收件方</button></form><form id="recipient-edit" class="hidden"><input type="hidden" name="rid"><label>名称<input name="name" required minlength="2"></label><label>收件地址<input name="address" required></label><label class="check"><input type="checkbox" name="enabled" value="1"> 启用(停用后不再生成新投递)</label><button type="submit" class="button small">保存修改</button></form>':'')
  +'<p class="hint">地址修改只影响之后的新投递;进行中的投递与重发旧件仍按快照地址发送。</p></section>';
 const inboxPanel='<section class="panel"><div class="section-title"><h2>演示收件端</h2><span>'+(box.drop_receipts?'回执通道故障中':'回执通道正常')+'</span></div>'
  +'<p class="hint">本机演示收件服务,地址 http://backend:8000/receiver/inbox 。开启故障后照常入件,但回执与查询返回 503,用于演示待确认、对账与迟到回执。</p>'
  +(canAdmin?'<button class="button small" id="toggle-inbox" data-drop="'+(box.drop_receipts?1:0)+'">'+(box.drop_receipts?'恢复回执通道':'模拟回执丢失')+'</button>':'')
  +'<div class="inbox-list">'+(box.items.length?box.items.map(i=>'<div class="delivery"><div><strong>回执 #'+i.id+' · 投递号 '+i.dispatch_id+'</strong><p>'+esc(i.filename)+' · '+esc(i.recipient)+'</p><small>'+date(i.received_at)+' · SHA256 '+esc(i.checksum.slice(0,16))+'…'+(i.duplicates?' · 重复拦截 '+i.duplicates+' 次':'')+'</small></div></div>').join(''):'<p class="empty">收件端暂无入件。</p>')+'</div></section>';
 return heading('06 / DELIVERY','投递确认与对账','归档完成不代表各编辑部已收到。按收件方确认投递:待发、待确认、已送达、失败、已撤销,每个环节留痕可核对。','<button class="button" id="refresh-dispatch">刷新 ↻</button>')+ledger+'<div class="two-columns">'+recipientsPanel+inboxPanel+'</div>';
}
function renderDetail(d){
 const el=document.querySelector('#dispatch-detail');
 el.innerHTML='<div class="detail-card"><div class="section-title"><h2>投递 #'+d.id+' 核对单</h2><span>'+esc(DispatchStatus[d.status]||d.status)+'</span></div>'
 +'<div class="metrics"><div><span>收件方</span><strong>'+esc(d.recipient_name)+'</strong></div><div><span>尝试次数</span><strong>'+d.attempts+'</strong></div><div><span>回执</span><strong>'+(d.receipt_id?'#'+esc(d.receipt_id):'—')+'</strong>'+(d.receipt_at?'<small>'+date(d.receipt_at)+'</small>':'')+'</div><div><span>撤销</span><strong>'+(d.revoked_at?'已申请':'—')+'</strong>'+(d.revoked_at?'<small>'+date(d.revoked_at)+'</small>':'')+'</div></div>'
 +(d.last_error?'<p class="warning">'+esc(d.last_error)+'</p>':'')
 +'<div class="table-wrap"><table><thead><tr><th>时间</th><th>动作</th><th>结果</th><th>说明</th></tr></thead><tbody>'+d.attempts_log.map(a=>'<tr><td>'+date(a.at)+'</td><td>'+esc(AttemptKind[a.kind]||a.kind)+'</td><td>'+esc(AttemptResult[a.result]||a.result)+'</td><td>'+esc(a.detail)+'</td></tr>').join('')+'</tbody></table></div></div>';
}
let timer=null;
export function bindDispatch(refresh){
 document.querySelector('#refresh-dispatch').onclick=refresh;
 if(timer)clearInterval(timer);
 timer=setInterval(()=>{if(route().page!=='dispatch'){clearInterval(timer);timer=null;return;}const det=document.querySelector('#dispatch-detail');if(det&&det.innerHTML)return;refresh();},5000);
 const create=document.querySelector('#recipient-form');
 if(create)submit(create,async f=>{await recipients.create({name:f.get('name'),address:f.get('address')});notify('收件方已添加');await refresh();});
 const edit=document.querySelector('#recipient-edit');
 document.querySelectorAll('[data-edit]').forEach(b=>b.onclick=()=>{edit.classList.remove('hidden');edit.querySelector('[name=rid]').value=b.dataset.edit;edit.querySelector('[name=name]').value=b.dataset.name;edit.querySelector('[name=address]').value=b.dataset.address;edit.querySelector('[name=enabled]').checked=b.dataset.enabled==='1';edit.scrollIntoView({behavior:'smooth'});});
 if(edit)submit(edit,async f=>{await recipients.update(Number(f.get('rid')),{name:f.get('name'),address:f.get('address'),enabled:f.get('enabled')==='1'});notify('收件方已更新;新地址只影响之后的新投递');await refresh();});
 const toggle=document.querySelector('#toggle-inbox');
 if(toggle)toggle.onclick=async()=>{try{const r=await inbox.mode(toggle.dataset.drop!=='1');notify(r.drop_receipts?'已开启回执丢失模拟:投递将转入待确认':'回执通道已恢复,待确认投递将自动对账');await refresh();}catch(e){notify(e.message,true);}};
 const rd=document.querySelector('#redispatch-form');
 if(rd)submit(rd,async f=>{await dispatches.redispatch(Number(f.get('delivery_id')),Number(f.get('recipient_id')));notify('补投已创建,快照当前地址');await refresh();});
 document.querySelectorAll('[data-detail]').forEach(b=>b.onclick=async()=>{try{renderDetail(await dispatches.get(b.dataset.detail));}catch(e){notify(e.message,true);}});
 document.querySelectorAll('[data-retry]').forEach(b=>b.onclick=async()=>{try{await dispatches.retry(b.dataset.retry);notify('已重新排队,沿用原投递号');await refresh();}catch(e){notify(e.message,true);}});
 document.querySelectorAll('[data-revoke]').forEach(b=>b.onclick=async()=>{if(!confirm('确认撤销该投递?尚未接收的将停止发送;若对方已接收,已接收事实保留。'))return;try{await dispatches.revoke(b.dataset.revoke);notify('已撤销,未接收的投递已停止发送');}catch(e){notify(e.message,true);}await refresh();});
}
