export const API=process.env.NEXT_PUBLIC_API_URL||"http://localhost:8000";
export function authToken(){return typeof window==='undefined'?'':localStorage.getItem('ai_token')||''}
export async function apiFetch(path:string,options:RequestInit={}){
 const headers:any={...(options.headers||{})};
 const t=authToken(); if(t) headers.Authorization=`Bearer ${t}`;
 if(options.body && !(options.body instanceof FormData) && !headers['Content-Type']) headers['Content-Type']='application/json';
 const r=await fetch(`${API}${path}`,{...options,headers,cache:'no-store'});
 if(r.status===401 && typeof window!=='undefined'){localStorage.removeItem('ai_token'); if(!location.pathname.startsWith('/login')) location.assign('/login');}
 return r;
}
