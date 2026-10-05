const configured=(process.env.NEXT_PUBLIC_API_URL||"").trim().replace(/\/$/,"");
export const API=configured || (typeof window!=="undefined" ? window.location.origin : "http://localhost:8000");
export function authToken(){return typeof window==='undefined'?'':localStorage.getItem('ai_token')||''}
export async function apiFetch(path:string,options:RequestInit={}){
 const headers:any={...(options.headers||{})};
 const t=authToken(); if(t) headers.Authorization=`Bearer ${t}`;
 if(options.body && !(options.body instanceof FormData) && !headers['Content-Type']) headers['Content-Type']='application/json';
 const url=`${API}${path}`;
 try{
  const r=await fetch(url,{...options,headers,cache:'no-store'});
  if(r.status===401 && typeof window!=='undefined'){localStorage.removeItem('ai_token'); if(!location.pathname.startsWith('/login')) location.assign('/login');}
  return r;
 }catch(err:any){
  const origin=typeof window!=='undefined'?window.location.origin:'browser';
  throw new Error(`Não foi possível acessar a API (${url}). Verifique NEXT_PUBLIC_API_URL, HTTPS e CORS para ${origin}. Detalhe: ${err?.message||err}`);
 }
}
