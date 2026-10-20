"use client";
import Link from "next/link";
import {useEffect,useRef,useState} from "react";
import {useRouter} from "next/navigation";
import UserAvatar from "./UserAvatar";
import {MoreVertical,Building2,ChevronDown,LogOut,ShieldCheck,UserRound} from "lucide-react";
import {saas} from "../lib/saas";

type Me={user:{name:string;email:string;role:string;avatar_version?:string};company:{name:string;status:string};subscription?:{plan:string;status:string}};
export default function WorkspaceHeader({onOpenMenu,menuButtonRef,menuOpen=false}:{onOpenMenu:()=>void;menuButtonRef:React.RefObject<HTMLButtonElement|null>;menuOpen?:boolean}){
 const router=useRouter(); const ref=useRef<HTMLDivElement>(null); const[me,setMe]=useState<Me|null>(null); const[open,setOpen]=useState(false);
 useEffect(()=>{const load=()=>{saas('/me').then(setMe).catch(()=>{})};load();window.addEventListener('profile-updated',load);return()=>window.removeEventListener('profile-updated',load)},[]);
 useEffect(()=>{const f=(e:MouseEvent)=>{if(ref.current&&!ref.current.contains(e.target as Node))setOpen(false)};document.addEventListener('mousedown',f);return()=>document.removeEventListener('mousedown',f)},[]);
 function logout(){localStorage.removeItem('ai_token');router.replace('/login');router.refresh()}
 return <header className="workspace-header">
   <button ref={menuButtonRef} className="icon-btn mobile-menu-button" onClick={onOpenMenu} aria-label="Abrir menu" aria-expanded={menuOpen} aria-controls="workspace-sidebar"><MoreVertical size={22}/></button><div className="workspace-context"><span className="workspace-icon"><Building2 size={18}/></span><div><small>EMPRESA / WORKSPACE</small><strong>{me?.company.name||'Carregando...'}</strong></div>{me?.subscription?.plan&&<span className="plan-chip">{me.subscription.plan}</span>}</div>
   <div className="user-menu-wrap" ref={ref}>
    <button className="user-menu-trigger" onClick={()=>setOpen(v=>!v)} aria-expanded={open}><UserAvatar name={me?.user.name||"Usuário"} version={me?.user.avatar_version}/><span className="user-copy"><strong>{me?.user.name||'Usuário'}</strong><small>{me?.user.role||''}</small></span><ChevronDown size={17}/></button>
    {open&&<div className="user-popover">
      <div className="user-popover-head"><UserAvatar name={me?.user.name||"Usuário"} version={me?.user.avatar_version} large/><div><strong>{me?.user.name}</strong><small>{me?.user.email}</small></div></div>
      <Link href="/perfil" onClick={()=>setOpen(false)}><UserRound size={17}/>Meu perfil</Link>
      <Link href="/seguranca" onClick={()=>setOpen(false)}><ShieldCheck size={17}/>Segurança</Link>
      <button onClick={logout}><LogOut size={17}/>Sair</button>
    </div>}
   </div>
 </header>
}
