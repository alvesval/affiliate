"use client";
import {useEffect,useRef,useState} from 'react';
import {usePathname} from 'next/navigation';
import Sidebar from './Sidebar';
import WorkspaceHeader from './WorkspaceHeader';

export default function WorkspaceShell({children}:{children:React.ReactNode}){
 const [collapsed,setCollapsed]=useState(false),[mobileOpen,setMobileOpen]=useState(false);
 const path=usePathname(),menuButton=useRef<HTMLButtonElement>(null),content=useRef<HTMLDivElement>(null);
 useEffect(()=>{try{setCollapsed(localStorage.getItem('affiliate-sidebar-collapsed')==='true')}catch{}},[]);
 useEffect(()=>setMobileOpen(false),[path]);
 function toggle(){setCollapsed(v=>{try{localStorage.setItem('affiliate-sidebar-collapsed',String(!v))}catch{}return !v})}
 function close(){setMobileOpen(false);content.current?.removeAttribute('inert');menuButton.current?.focus()}
 useEffect(()=>{if(!mobileOpen)return;const old=document.body.style.overflow;document.body.style.overflow='hidden';content.current?.setAttribute('inert','');const small=window.matchMedia('(max-width: 750px)');const resize=()=>{if(!small.matches)setMobileOpen(false)};small.addEventListener('change',resize);
  const escape=(e:KeyboardEvent)=>{if(e.key==='Escape'){e.preventDefault();close()}};document.addEventListener('keydown',escape);return()=>{document.body.style.overflow=old;content.current?.removeAttribute('inert');small.removeEventListener('change',resize);document.removeEventListener('keydown',escape)};
 },[mobileOpen]);
 return <div className={`shell ${collapsed?'sidebar-collapsed':''} ${mobileOpen?'mobile-menu-open':''}`}>
  {mobileOpen&&<button className="sidebar-overlay" aria-label="Fechar menu" onClick={close}/>}
  <Sidebar collapsed={collapsed} onToggle={toggle} mobileOpen={mobileOpen} onClose={close}/>
  <div className="workspace-area" ref={content}><WorkspaceHeader onOpenMenu={()=>setMobileOpen(true)} menuButtonRef={menuButton} menuOpen={mobileOpen}/><main className="main">{children}</main></div>
 </div>;
}
