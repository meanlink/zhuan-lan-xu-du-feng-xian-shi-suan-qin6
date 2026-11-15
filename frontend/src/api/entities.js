import {api} from './client.js';
export const datasets={list:()=>api('/datasets'),get:id=>api('/datasets/'+id),create:data=>api('/datasets',{method:'POST',body:JSON.stringify(data)})};
export const jobs={list:()=>api('/jobs'),get:id=>api('/jobs/'+id),create:data=>api('/jobs',{method:'POST',body:JSON.stringify(data)}),approve:id=>api('/jobs/'+id+'/approve',{method:'POST'})};
export const reports={list:()=>api('/reports'),create:data=>api('/reports',{method:'POST',body:JSON.stringify(data)}),toggle:id=>api('/reports/'+id+'/toggle',{method:'POST'}),deliveries:()=>api('/deliveries')};
export const recipients={list:()=>api('/recipients'),create:data=>api('/recipients',{method:'POST',body:JSON.stringify(data)}),update:(id,data)=>api('/recipients/'+id,{method:'PATCH',body:JSON.stringify(data)})};
export const dispatches={list:()=>api('/dispatches'),get:id=>api('/dispatches/'+id),retry:id=>api('/dispatches/'+id+'/retry',{method:'POST'}),revoke:id=>api('/dispatches/'+id+'/revoke',{method:'POST'}),redispatch:(delivery,recipient_id)=>api('/deliveries/'+delivery+'/dispatches',{method:'POST',body:JSON.stringify({recipient_id})})};
export const inbox={view:()=>api('/inbox'),mode:drop_receipts=>api('/inbox/mode',{method:'POST',body:JSON.stringify({drop_receipts})})};
