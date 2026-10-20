"use client";
import {useEffect,useState} from 'react';
import {apiFetch} from '../lib/api';

export default function UserAvatar({name,version='',large=false}:{name:string;version?:string;large?:boolean}){
 const [source,setSource]=useState('');
 useEffect(()=>{let cancelled=false,url='';setSource('');if(!version)return;
  (async()=>{try{const r=await apiFetch('/api/v1/saas/profile/avatar');if(!r.ok)return;const blob=await r.blob();if(cancelled)return;url=URL.createObjectURL(blob);setSource(url)}catch{}})();
  return()=>{cancelled=true;if(url)URL.revokeObjectURL(url)};
 },[version]);
 const initials=(name||'U').trim().split(/\s+/).slice(0,2).map(x=>x[0]).join('').toUpperCase();
 return <span className={`user-avatar ${large?'large':''}`}>{source?<img src={source} alt={`Foto de ${name||'perfil'}`}/>:initials}</span>;
}
