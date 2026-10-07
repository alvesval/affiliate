"use client";
import {useEffect,useMemo,useState} from "react";
import Link from "next/link";
import {ArrowRight,ArrowUpRight,CheckCircle2,Clapperboard,Lightbulb,Link2,PackageSearch,Radio,RefreshCw,Sparkles,Store} from "lucide-react";
import {apiFetch} from "../../../lib/api";
import OnboardingCard from "../../../components/OnboardingCard";

type Summary={products:number;opportunities:number;marketplaces:number;publications:number;published:number;queued:number;failed:number;top:any[]};
const initial:Summary={products:0,opportunities:0,marketplaces:0,publications:0,published:0,queued:0,failed:0,top:[]};
export default function Home(){
 const[d,setD]=useState<Summary>(initial);const[loading,setLoading]=useState(true);
 useEffect(()=>{apiFetch('/api/v1/dashboard/summary').then(async r=>{if(r.ok)setD(await r.json())}).finally(()=>setLoading(false))},[]);
 const recommendation=useMemo(()=>d.top?.[0]||null,[d.top]);
 const cards=[
  {label:'Produtos no catálogo',value:d.products,Icon:PackageSearch,helper:'Itens disponíveis no workspace'},
  {label:'Oportunidades',value:d.opportunities,Icon:Sparkles,helper:'Produtos com link monetizável'},
  {label:'Publicações',value:d.publications,Icon:Radio,helper:d.published?`${d.published} publicadas com sucesso`:'Nenhuma publicação concluída'},
  {label:'Marketplaces',value:d.marketplaces,Icon:Store,helper:'Fontes presentes no catálogo'}
 ];
 return <>
  <div className="commercial-hero"><div><span className="eyebrow">CENTRAL DE DECISÃO</span><h1>O que merece sua atenção hoje.</h1><p>Produtos, conteúdo e distribuição em uma visão única — sem inventar métricas que ainda não foram coletadas.</p></div><div className="hero-actions"><Link className="btn ghost" href="/produtos">Ver produtos</Link><Link className="btn primary" href="/conteudos"><Clapperboard size={16}/> Criar conteúdo</Link></div></div>
  <OnboardingCard/>
  <div className="commercial-kpis">{cards.map(({label,value,Icon,helper})=><div className="kpi-card" key={label}><div className="kpi-icon"><Icon size={19}/></div><div><p>{label}</p><strong>{loading?'—':value}</strong><small>{helper}</small></div></div>)}</div>
  <div className="decision-grid">
   <section className="card ai-recommendation"><div className="section-head"><div><span className="eyebrow"><Lightbulb size={13}/> IA RECOMENDA</span><h2>Próxima melhor ação</h2></div><span className="live-chip">Dados do catálogo</span></div>
    {recommendation?<div className="recommendation-body"><div className="score-orb"><span>Score</span><b>{recommendation.score}</b></div><div className="recommendation-copy"><h3>{recommendation.title}</h3><p>{recommendation.marketplace} · {Number(recommendation.price).toLocaleString('pt-BR',{style:'currency',currency:'BRL'})}</p><p className="muted">Este produto aparece no topo do score atual e já possui condição para divulgação. Revise o produto e prepare uma campanha.</p><Link className="btn primary" href="/conteudos">Criar campanha <ArrowRight size={15}/></Link></div></div>:<div className="empty commercial-empty"><Sparkles size={24}/><strong>Ainda não há recomendação disponível</strong><span>Adicione um produto com link de afiliado para a inteligência começar a priorizar oportunidades.</span><Link className="btn primary" href="/produtos">Adicionar produto</Link></div>}
   </section>
   <section className="card operation-card"><div className="section-head"><div><span className="eyebrow">OPERAÇÃO</span><h2>Saúde das publicações</h2></div><RefreshCw size={17}/></div>
    <div className="status-stack"><div><span><CheckCircle2 size={16}/> Publicadas</span><b>{d.published}</b></div><div><span><Radio size={16}/> Na fila</span><b>{d.queued}</b></div><div><span><Link2 size={16}/> Com erro</span><b>{d.failed}</b></div></div>
    <Link className="text-link" href="/conteudos">Abrir Estúdio IA <ArrowUpRight size={14}/></Link>
   </section>
  </div>
  <section className="card opportunity-panel"><div className="section-head"><div><span className="eyebrow">OPORTUNIDADES</span><h2>Produtos priorizados</h2><p className="muted">Ranking calculado somente com os dados disponíveis no catálogo.</p></div><Link className="btn ghost" href="/oportunidades">Ver todas <ArrowUpRight size={14}/></Link></div>
   {d.top?.length?<div className="opportunity-list">{d.top.slice(0,5).map((x:any,i:number)=><div className="opportunity-row" key={x.id}><span className="rank">{String(i+1).padStart(2,'0')}</span><div className="opportunity-name"><strong>{x.title}</strong><small>{x.marketplace} · {Number(x.price).toLocaleString('pt-BR',{style:'currency',currency:'BRL'})}</small></div><div className="opportunity-score"><span>Score AIA</span><b>{x.score}</b></div><Link href="/conteudos" className="row-action">Criar conteúdo <ArrowRight size={14}/></Link></div>)}</div>:<div className="empty">Nenhuma oportunidade calculada ainda.</div>}
  </section>
 </>
}
