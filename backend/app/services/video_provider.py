from __future__ import annotations
import httpx
from fastapi import HTTPException
from app.core.config import settings

class VideoProvider:
    name='base'
    async def start(self,prompt:str,seconds:int)->dict: raise NotImplementedError
    async def status(self,job_id:str)->dict: raise NotImplementedError
    async def download(self,job_id:str)->bytes: raise NotImplementedError

class FalVideoProvider(VideoProvider):
    name='fal'
    def __init__(self):
        self.key=settings.fal_key
        self.model=settings.fal_video_model.strip('/')
        self.base=f'https://queue.fal.run/{self.model}'
    def headers(self):
        if not self.key: raise HTTPException(503,'Vídeo IA não configurado. Configure FAL_KEY no Railway.')
        return {'Authorization':f'Key {self.key}','Content-Type':'application/json'}
    async def start(self,prompt:str,seconds:int)->dict:
        seconds=max(3,min(15,int(seconds)))
        payload={'prompt':prompt,'duration':str(seconds),'aspect_ratio':'9:16','generate_audio':False}
        async with httpx.AsyncClient(timeout=60) as c:
            r=await c.post(self.base,headers=self.headers(),json=payload)
        if r.status_code>=400: raise HTTPException(502,f'Falha ao iniciar vídeo IA/fal ({r.status_code}): {r.text[:300]}')
        d=r.json(); rid=d.get('request_id')
        if not rid: raise HTTPException(502,'fal.ai não retornou request_id para o vídeo.')
        return {'id':rid,'status':'queued','progress':0,'seconds':seconds,'provider':self.name,'model':self.model}
    async def _status_raw(self,job_id:str):
        async with httpx.AsyncClient(timeout=45) as c:
            r=await c.get(f'{self.base}/requests/{job_id}/status',headers=self.headers())
        if r.status_code>=400: raise HTTPException(502,f'Falha ao consultar vídeo IA/fal ({r.status_code}): {r.text[:250]}')
        return r.json()
    async def status(self,job_id:str)->dict:
        d=await self._status_raw(job_id); raw=str(d.get('status','')).upper()
        if raw=='COMPLETED': status='completed'; progress=100
        elif raw in ('IN_PROGRESS','RUNNING'): status='in_progress'; progress=50
        elif raw in ('IN_QUEUE','QUEUED'): status='queued'; progress=5
        else: status='failed' if raw in ('FAILED','ERROR','CANCELLED') else raw.lower()
        return {'id':job_id,'status':status,'progress':progress,'error':d.get('error') or {},'provider':self.name,'model':self.model}
    async def _result(self,job_id:str)->dict:
        async with httpx.AsyncClient(timeout=60) as c:
            r=await c.get(f'{self.base}/requests/{job_id}',headers=self.headers())
        if r.status_code>=400: raise HTTPException(502,f'Falha ao obter resultado do vídeo IA/fal ({r.status_code}): {r.text[:250]}')
        return r.json()
    async def download(self,job_id:str)->bytes:
        d=await self._result(job_id); video=d.get('video') or {}; url=video.get('url')
        if not url: raise HTTPException(502,'fal.ai concluiu a geração, mas não retornou URL do vídeo.')
        async with httpx.AsyncClient(timeout=180,follow_redirects=True) as c:r=await c.get(url)
        if r.status_code>=400: raise HTTPException(502,f'Falha ao baixar vídeo gerado ({r.status_code}).')
        return r.content

def get_video_provider()->VideoProvider:
    provider=(settings.video_provider or 'fal').strip().lower()
    if provider=='fal': return FalVideoProvider()
    raise HTTPException(503,f'VIDEO_PROVIDER não suportado: {provider}')
