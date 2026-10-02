"use client";
import Link from "next/link";
import {useEffect,useRef,useState} from "react";
import {useRouter} from "next/navigation";
import {Building2,ChevronDown,LogOut,ShieldCheck,UserRound} from "lucide-react";
import {saas} from "../lib/saas";

type Me={user:{name:string;email:string;role:string};company:{name:string;status:string};subscription?:{plan:string;status:string}};
export default function WorkspaceHeader(){
 const router=useRouter(); const ref=useRef<HTMLDivElement>(null); const[me,setMe]=useState<Me|null>(null); const[open,setOpen]=useState(false);
 useEffect(()=>{saas('/me').then(setMe).catch(()=>{});},[]);
 useEffect(()=>{const f=(e:MouseEvent)=>{if(ref.current&&!ref.current.contains(e.target as Node))setOpen(false)};document.addEventListener('mousedown',f);return()=>document.removeEventListener('mousedown',f)},[]);
 function logout(){localStorage.removeItem('ai_token');router.replace('/login');router.refresh()}
 const initials=(me?.user.name||'U').split(/\s+/).slice(0,2).map(x=>x[0]).join('').toUpperCase();
 return <header className="workspace-header">
   <div className="workspace-context"><span className="workspace-icon"><Building2 size={18}/></span><div><small>EMPRESA / WORKSPACE</small><strong>{me?.company.name||'Carregando...'}</strong></div>{me?.subscription?.plan&&<span className="plan-chip">{me.subscription.plan}</span>}</div>
   <div className="user-menu-wrap" ref={ref}>
    <button className="user-menu-trigger" onClick={()=>setOpen(v=>!v)} aria-expanded={open}><span className="user-avatar">{initials}</span><span className="user-copy"><strong>{me?.user.name||'Usuário'}</strong><small>{me?.user.role||''}</small></span><ChevronDown size={17}/></button>
    {open&&<div className="user-popover">
      <div className="user-popover-head"><span className="user-avatar large">{initials}</span><div><strong>{me?.user.name}</strong><small>{me?.user.email}</small></div></div>
      <Link href="/perfil" onClick={()=>setOpen(false)}><UserRound size={17}/>Meu perfil</Link>
      <Link href="/seguranca" onClick={()=>setOpen(false)}><ShieldCheck size={17}/>Segurança</Link>
      <button onClick={logout}><LogOut size={17}/>Sair</button>
    </div>}
   </div>
 </header>
}
