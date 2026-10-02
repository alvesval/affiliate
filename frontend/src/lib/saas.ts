export const API=process.env.NEXT_PUBLIC_API_URL||"http://localhost:8000";
export function token(){return typeof window==='undefined'?'':localStorage.getItem('ai_token')||''}
export async function saas(path:string,options:RequestInit={}){
 const headers:any={...(options.headers||{}),'Content-Type':'application/json'};
 const t=token();if(t)headers.Authorization=`Bearer ${t}`;
 const r=await fetch(`${API}/api/v1/saas${path}`,{...options,headers,cache:'no-store'});
 const d=await r.json().catch(()=>({}));if(!r.ok)throw new Error(d.detail||`HTTP ${r.status}`);return d;
}
