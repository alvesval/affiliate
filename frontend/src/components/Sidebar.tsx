"use client";
import Link from "next/link";
import Image from "next/image";
import {usePathname} from "next/navigation";
import {LayoutDashboard,PackageSearch,Sparkles,PlugZap,Clapperboard,Users,WalletCards,Bot} from "lucide-react";
const items=[{href:"/dashboard",label:"Visão geral",Icon:LayoutDashboard},{href:"/produtos",label:"Catálogo",Icon:PackageSearch},{href:"/oportunidades",label:"Oportunidades",Icon:Sparkles},{href:"/conteudos",label:"Estúdio de conteúdo",Icon:Clapperboard},{href:"/integracoes",label:"Integrações",Icon:PlugZap},{href:"/automacao",label:"Automação",Icon:Bot},{href:"/equipe",label:"Equipe",Icon:Users},{href:"/plano",label:"Plano",Icon:WalletCards}];
export default function Sidebar(){const path=usePathname();return <aside className="side"><Link href="/dashboard" className="brand brand-logo"><Image src="/ai-affiliate-logo.png" alt="AIAffiliateIntelligence" width={178} height={72} priority/></Link><div className="nav-heading">WORKSPACE</div><nav className="nav">{items.map(({href,label,Icon})=><Link key={href} href={href} className={path===href?"active":""}><Icon size={18}/>{label}</Link>)}</nav><div className="side-footer"><span className="status-dot"/> Ambiente seguro <small>V1.9.4 · SaaS Workspace</small></div></aside>}
