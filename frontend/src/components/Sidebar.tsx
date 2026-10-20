"use client";
import Link from "next/link";
import Image from "next/image";
import {usePathname} from "next/navigation";
import {useEffect,useState} from "react";
import {LayoutDashboard,PackageSearch,Sparkles,PlugZap,Clapperboard,Users,WalletCards,Bot,TrendingUp,Building2,BarChart3,Settings2,MessageSquare,Headphones} from "lucide-react";
import {API,authToken} from "../lib/api";

type NavItem={href:string;label:string;Icon:any};
const sections:{title:string;items:NavItem[]}[]=[
 {title:"VISÃO GERAL",items:[{href:"/dashboard",label:"Home",Icon:LayoutDashboard},{href:"/oportunidades",label:"Oportunidades",Icon:Sparkles}]},
 {title:"CRIAR E PUBLICAR",items:[{href:"/produtos",label:"Produtos",Icon:PackageSearch},{href:"/conteudos",label:"Estúdio IA",Icon:Clapperboard},{href:"/automacao",label:"Automação",Icon:Bot}]},
 {title:"CONFIGURAÇÃO",items:[{href:"/suporte",label:"Ajuda e suporte",Icon:MessageSquare},{href:"/integracoes",label:"Integrações",Icon:PlugZap},{href:"/equipe",label:"Equipe",Icon:Users},{href:"/plano",label:"Plano e uso",Icon:WalletCards}]},
];
const admin:NavItem[]=[{href:"/atendimento",label:"Atendimento",Icon:Headphones},{href:"/crescimento",label:"Crescimento",Icon:TrendingUp},{href:"/clientes",label:"Clientes",Icon:Building2},{href:"/precos",label:"Planos e preços",Icon:WalletCards}];
export default function Sidebar(){
 const path=usePathname();const[isAdmin,setAdmin]=useState(false);const[counts,setCounts]=useState({customer:0,admin:0});
 useEffect(()=>{let alive=true;async function load(){try{const r=await fetch(`${API}/api/v1/support/unread`,{headers:{Authorization:`Bearer ${authToken()}`},cache:"no-store"});if(r.ok&&alive)setCounts(await r.json())}catch{}}void load();const timer=setInterval(()=>{if(document.visibilityState==="visible")void load()},30000);window.addEventListener("support-updated",load);window.addEventListener("focus",load);return()=>{alive=false;clearInterval(timer);window.removeEventListener("support-updated",load);window.removeEventListener("focus",load)}},[]);
 useEffect(()=>{fetch(`${API}/api/v1/growth/admin/access`,{headers:{Authorization:`Bearer ${authToken()}`}}).then(r=>setAdmin(r.ok)).catch(()=>setAdmin(false))},[]);
 const render=(x:NavItem)=><Link key={x.href} href={x.href} className={path===x.href?"active":""}><x.Icon size={18}/><span>{x.label}</span>{((x.href==="/suporte"?counts.customer:x.href==="/atendimento"?counts.admin:0)>0)&&<small className="support-nav-count">{x.href==="/suporte"?counts.customer:counts.admin}</small>}</Link>;
 return <aside className="side"><Link href="/dashboard" className="brand brand-logo"><Image src="/ai-affiliate-logo.png" alt="AIAffiliate Intelligence" width={178} height={72} priority/></Link>
  <div className="nav-scroll">{sections.map(s=><div className="nav-section" key={s.title}><div className="nav-heading">{s.title}</div><nav className="nav">{s.items.map(render)}</nav></div>)}
  {isAdmin&&<div className="nav-section"><div className="nav-heading">ADMINISTRAÇÃO</div><nav className="nav">{admin.map(render)}</nav></div>}</div>
  <div className="side-footer"><span className="status-dot"/> Operação ativa <small>V1 Commercial · RC7</small></div>
 </aside>
}
