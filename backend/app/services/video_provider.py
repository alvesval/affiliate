from __future__ import annotations
import logging
from urllib.parse import urlparse
import httpx
from fastapi import HTTPException
from app.core.config import settings

logger = logging.getLogger(__name__)

class VideoProvider:
    name='base'
    async def start(self,prompt:str,seconds:int,images:list[str]|None=None)->dict: raise NotImplementedError
    async def status(self,job_id:str,status_url:str|None=None)->dict: raise NotImplementedError
    async def download(self,job_id:str,response_url:str|None=None)->bytes: raise NotImplementedError

class FalVideoProvider(VideoProvider):
    name='fal'
    def __init__(self):
        self.key=settings.fal_key
        self.model=settings.fal_video_model.strip('/')
        self.base=f'https://queue.fal.run/{self.model}'

    def headers(self):
        if not self.key:
            raise HTTPException(503,'Vídeo IA não configurado. Configure FAL_KEY no Railway.')
        return {'Authorization':f'Key {self.key}','Content-Type':'application/json'}

    @staticmethod
    def _safe_queue_url(url:str|None,fallback:str)->str:
        """Use URLs returned by fal Queue itself; reject arbitrary hosts to avoid SSRF."""
        candidate=(url or '').strip()
        if not candidate:
            return fallback
        try:
            p=urlparse(candidate)
            host=(p.hostname or '').lower()
            if p.scheme=='https' and (host=='queue.fal.run' or host.endswith('.fal.run')):
                return candidate
        except Exception:
            pass
        logger.warning('[FAL] URL de fila inválida recebida; usando fallback. host=%s', urlparse(candidate).hostname if candidate else '')
        return fallback

    async def start(self,prompt:str,seconds:int,images:list[str]|None=None)->dict:
        seconds=max(3,min(15,int(seconds)))
        refs=[x for x in (images or []) if x][:3]
        model=(settings.fal_image_video_model if refs else self.model).strip('/')
        base=f'https://queue.fal.run/{model}'
        if refs:
            # The real product is an explicit visual element. Primary image is also the first frame.
            payload={'prompt':prompt,'duration':str(seconds),'start_image_url':refs[0],'generate_audio':False,
                     'negative_prompt':'distorted package, altered logo, changed label, invented text, wrong product, blur, low quality',
                     'cfg_scale':0.65}
            if len(refs)>1:
                payload['elements']=[{'frontal_image_url':refs[0],'reference_image_urls':refs[1:]}]
        else:
            payload={'prompt':prompt,'duration':str(seconds),'aspect_ratio':'9:16','generate_audio':False}
        logger.info('[FAL] Submit iniciado model=%s duration=%ss visual_refs=%s',model,seconds,len(refs))
        async with httpx.AsyncClient(timeout=60) as c:
            r=await c.post(base,headers=self.headers(),json=payload)
        if r.status_code>=400:
            logger.error('[FAL] Submit falhou HTTP=%s body=%s',r.status_code,r.text[:500])
            raise HTTPException(502,f'Falha ao iniciar vídeo IA/fal ({r.status_code}): {r.text[:300]}')
        d=r.json(); rid=d.get('request_id')
        if not rid:
            logger.error('[FAL] Submit sem request_id response=%s',str(d)[:500])
            raise HTTPException(502,'fal.ai não retornou request_id para o vídeo.')
        # IMPORTANT: fal returns canonical queue URLs. They can differ from simply
        # appending /requests/... to a model endpoint, so preserve and reuse them.
        status_url=self._safe_queue_url(d.get('status_url'),f'{base}/requests/{rid}/status')
        response_url=self._safe_queue_url(d.get('response_url'),f'{base}/requests/{rid}')
        logger.info('[FAL] Submit aceito request_id=%s status_url=%s response_url=%s',rid,status_url,response_url)
        return {'id':rid,'status':'queued','progress':0,'seconds':seconds,'provider':self.name,'model':model,'status_url':status_url,'response_url':response_url}

    async def _status_raw(self,job_id:str,status_url:str|None=None):
        fallback=f'{self.base}/requests/{job_id}/status'
        url=self._safe_queue_url(status_url,fallback)
        logger.info('[FAL] Consultando status request_id=%s url=%s',job_id,url)
        async with httpx.AsyncClient(timeout=45) as c:
            r=await c.get(url,headers=self.headers())
        if r.status_code>=400:
            logger.error('[FAL] Status falhou request_id=%s HTTP=%s method=GET url=%s body=%s',job_id,r.status_code,url,r.text[:500])
            raise HTTPException(502,f'Falha ao consultar vídeo IA/fal ({r.status_code}): {r.text[:250]}')
        return r.json()

    async def status(self,job_id:str,status_url:str|None=None)->dict:
        d=await self._status_raw(job_id,status_url); raw=str(d.get('status','')).upper()
        if raw=='COMPLETED': status='completed'; progress=100
        elif raw in ('IN_PROGRESS','RUNNING'): status='in_progress'; progress=50
        elif raw in ('IN_QUEUE','QUEUED'): status='queued'; progress=5
        else: status='failed' if raw in ('FAILED','ERROR','CANCELLED') else raw.lower()
        logger.info('[FAL] Status request_id=%s status=%s',job_id,raw or 'UNKNOWN')
        return {'id':job_id,'status':status,'progress':progress,'error':d.get('error') or {},'provider':self.name,'model':self.model}

    async def _result(self,job_id:str,response_url:str|None=None)->dict:
        fallback=f'{self.base}/requests/{job_id}'
        url=self._safe_queue_url(response_url,fallback)
        logger.info('[FAL] Obtendo resultado request_id=%s url=%s',job_id,url)
        async with httpx.AsyncClient(timeout=60) as c:
            r=await c.get(url,headers=self.headers())
        if r.status_code>=400:
            logger.error('[FAL] Resultado falhou request_id=%s HTTP=%s method=GET url=%s body=%s',job_id,r.status_code,url,r.text[:500])
            raise HTTPException(502,f'Falha ao obter resultado do vídeo IA/fal ({r.status_code}): {r.text[:250]}')
        return r.json()

    async def download(self,job_id:str,response_url:str|None=None)->bytes:
        d=await self._result(job_id,response_url); video=d.get('video') or {}; url=video.get('url')
        if not url:
            logger.error('[FAL] Resultado sem video.url request_id=%s response=%s',job_id,str(d)[:500])
            raise HTTPException(502,'fal.ai concluiu a geração, mas não retornou URL do vídeo.')
        logger.info('[FAL] Baixando vídeo concluído request_id=%s',job_id)
        async with httpx.AsyncClient(timeout=180,follow_redirects=True) as c:
            r=await c.get(url)
        if r.status_code>=400:
            logger.error('[FAL] Download falhou request_id=%s HTTP=%s',job_id,r.status_code)
            raise HTTPException(502,f'Falha ao baixar vídeo gerado ({r.status_code}).')
        logger.info('[FAL] Vídeo baixado request_id=%s bytes=%s',job_id,len(r.content))
        return r.content

def get_video_provider()->VideoProvider:
    provider=(settings.video_provider or 'fal').strip().lower()
    if provider=='fal': return FalVideoProvider()
    raise HTTPException(503,f'VIDEO_PROVIDER não suportado: {provider}')
