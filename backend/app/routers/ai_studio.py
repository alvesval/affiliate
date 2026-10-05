from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from sqlalchemy import select
from datetime import datetime
import json
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.auth import require_role,Principal
from app.models.entities import Product
from app.models.social import ContentCampaign,ContentVariant
from app.models.saas import Subscription,Plan,UsageCounter
from app.services.ai_content import generate_copy,start_video,video_status,download_video
from app.services.media_storage import build_key,put_bytes,delete as delete_media
router=APIRouter(prefix='/api/v1/ai-studio',tags=['AI Content Studio'])
class GenerateIn(BaseModel):variant_id:int
class VideoIn(BaseModel):
    variant_id:int;seconds:int=Field(default=8,ge=4,le=12);prompt:str=Field(default='',max_length=5000)
class StatusIn(BaseModel):variant_id:int;video_id:str=Field(min_length=3,max_length=300)
def ctx(db,cid,vid):
    v=db.scalar(select(ContentVariant).where(ContentVariant.id==vid,ContentVariant.company_id==cid))
    if not v:raise HTTPException(404,'Variação não encontrada')
    c=db.scalar(select(ContentCampaign).where(ContentCampaign.id==v.campaign_id,ContentCampaign.company_id==cid));pr=db.scalar(select(Product).where(Product.id==c.product_id,Product.company_id==cid)) if c else None
    if not c or not pr:raise HTTPException(404,'Campanha/produto não encontrado')
    return v,c,pr
@router.get('/status')
def configured(p:Principal=Depends(require_role('EDITOR'))):
    from app.core.config import settings
    return {'configured':bool(settings.openai_api_key),'text_model':settings.openai_text_model,'video_model':settings.openai_video_model}
@router.post('/generate')
async def generate(x:GenerateIn,p:Principal=Depends(require_role('EDITOR')),db:Session=Depends(get_db)):
    v,c,pr=ctx(db,p.company_id,x.variant_id);d=await generate_copy(pr,v.platform,c.duration_seconds,c.tone,c.audience)
    v.title=str(d.get('title') or pr.title)[:300];v.hook=str(d.get('hook') or '')[:500];v.script=str(d.get('script') or '');v.caption=str(d.get('caption') or '');v.hashtags=str(d.get('hashtags') or '');v.cta=str(d.get('cta') or '')[:500];db.commit()
    return {'variant_id':v.id,'video_prompt':str(d.get('video_prompt') or '')}
@router.post('/video/start')
async def video_start(x:VideoIn,p:Principal=Depends(require_role('EDITOR')),db:Session=Depends(get_db)):
    v,c,pr=ctx(db,p.company_id,x.variant_id)
    sub=db.scalar(select(Subscription).where(Subscription.company_id==p.company_id))
    plan_code=(sub.plan_code if sub else 'ENTRY').upper()
    plan=db.scalar(select(Plan).where(Plan.code==plan_code))
    limits=json.loads(plan.limits_json or '{}') if plan else {}
    limit=int(limits.get('ai_video_month',0) or 0)
    key=datetime.utcnow().strftime('%Y-%m')
    usage=db.scalar(select(UsageCounter).where(UsageCounter.company_id==p.company_id,UsageCounter.period_key==key))
    used=int(getattr(usage,'ai_video_generations',0) or 0) if usage else 0
    if limit <= 0:
        raise HTTPException(402,f'O plano {plan_code} não inclui geração de vídeo com IA. Faça upgrade em Plano e assinatura.')
    if used >= limit:
        raise HTTPException(402,f'Limite mensal de vídeos IA atingido ({used}/{limit}). Faça upgrade do plano para continuar.')
    prompt=x.prompt.strip() or f'Vertical 9:16 social ad for {pr.title}. Clean product presentation, no invented claims or on-screen prices.'
    d=await start_video(prompt,x.seconds)
    if not usage:
        usage=UsageCounter(company_id=p.company_id,period_key=key)
        db.add(usage)
    usage.ai_video_generations=used+1
    db.commit()
    return {'variant_id':v.id,'video_id':d.get('id'),'status':d.get('status'),'progress':d.get('progress',0),'seconds':d.get('seconds'),'usage':{'used':used+1,'limit':limit}}
@router.post('/video/status')
async def poll(x:StatusIn,p:Principal=Depends(require_role('EDITOR')),db:Session=Depends(get_db)):
    v,c,pr=ctx(db,p.company_id,x.variant_id);d=await video_status(x.video_id);status=d.get('status','')
    if status=='completed':
        raw=await download_video(x.video_id);old=v.media_storage_key;key=build_key(v.id,'ai-video.mp4');put_bytes(key,raw,'video/mp4');v.media_storage_key=key;v.media_filename='ai-video.mp4';v.media_content_type='video/mp4';v.media_size=len(raw);v.media_duration_seconds=int(d.get('seconds') or 0);v.media_url='';db.commit();delete_media(old)
    err=d.get('error') or {};return {'variant_id':v.id,'video_id':x.video_id,'status':status,'progress':d.get('progress',0),'error':err.get('message') if isinstance(err,dict) else str(err or ''),'attached':bool(v.media_storage_key)}
