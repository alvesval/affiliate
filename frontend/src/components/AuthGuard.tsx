"use client";
import {useEffect,useState} from "react";
import {useRouter} from "next/navigation";
import {saas} from "../lib/saas";
export default function AuthGuard({children}:{children:React.ReactNode}){
 const router=useRouter(); const [ready,setReady]=useState(false);
 useEffect(()=>{const t=localStorage.getItem('ai_token');if(!t){router.replace('/login');return}saas('/me').then(()=>setReady(true)).catch(()=>{localStorage.removeItem('ai_token');router.replace('/login')})},[router]);
 if(!ready)return <main className="main"><div className="card"><p className="muted">Validando sessão...</p></div></main>;
 return <>{children}</>;
}
