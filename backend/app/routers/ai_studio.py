from fastapi import APIRouter,Depends,HTTPException,UploadFile,File
from pydantic import BaseModel,Field
from sqlalchemy import select
from datetime import datetime
import hashlib, io, ipaddress, socket
from urllib.parse import urlparse
import httpx
from PIL import Image
import json
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.auth import require_role,Principal
from app.models.entities import Product
from app.models.social import ContentCampaign,ContentVariant,ProductVisualReference
from app.models.saas import Subscription,Plan,UsageCounter
from app.services.ai_content import generate_copy,start_video,video_status,download_video
from app.services.media_storage import build_key,put_bytes,get_bytes,presigned_get_url,delete as delete_media,MediaStorageError
router=APIRouter(prefix='/api/v1/ai-studio',tags=['AI Content Studio'])
class GenerateIn(BaseModel):variant_id:int
class VideoIn(BaseModel):
    variant_id:int;seconds:int=Field(default=8,ge=4,le=12);prompt:str=Field(default='',max_length=5000)
class StatusIn(BaseModel):
    variant_id:int
    video_id:str=Field(min_length=3,max_length=300)
    status_url:str=Field(default='',max_length=2000)
    response_url:str=Field(default='',max_length=2000)
def ctx(db,cid,vid):
    v=db.scalar(select(ContentVariant).where(ContentVariant.id==vid,ContentVariant.company_id==cid))
    if not v:raise HTTPException(404,'Variação não encontrada')
    c=db.scalar(select(ContentCampaign).where(ContentCampaign.id==v.campaign_id,ContentCampaign.company_id==cid));pr=db.scalar(select(Product).where(Product.id==c.product_id,Product.company_id==cid)) if c else None
    if not c or not pr:raise HTTPException(404,'Campanha/produto não encontrado')
    return v,c,pr

IMAGE_TYPES={'image/jpeg','image/png','image/webp'}
MAX_REFERENCE_BYTES=12*1024*1024

def _visual_json(x):
    return {'id':x.id,'filename':x.filename,'content_type':x.content_type,'size_bytes':x.size_bytes,'width':x.width,'height':x.height,'sha256':x.sha256,'source_type':x.source_type,'source_url':x.source_url,'is_primary':x.is_primary,'position':x.position,'validated_at':x.validated_at.isoformat() if x.validated_at else None}

def _inspect_image(raw:bytes,ctype:str):
    if len(raw)>MAX_REFERENCE_BYTES: raise HTTPException(413,'Imagem excede 12 MB.')
    try:
        im=Image.open(io.BytesIO(raw)); im.verify(); im=Image.open(io.BytesIO(raw)); w,h=im.size; fmt=(im.format or '').upper()
    except Exception: raise HTTPException(422,'Arquivo de imagem inválido ou corrompido.')
    expected={'JPEG':'image/jpeg','PNG':'image/png','WEBP':'image/webp'}.get(fmt)
    if not expected or expected not in IMAGE_TYPES: raise HTTPException(415,'Use JPG, PNG ou WebP.')
    if w<300 or h<300: raise HTTPException(422,'A referência precisa ter no mínimo 300 px em cada lado.')
    ratio=w/h
    if ratio<0.40 or ratio>2.50: raise HTTPException(422,'Proporção da imagem fora do intervalo seguro 1:2,5 a 2,5:1.')
    return expected,w,h

def _assert_public_https(url:str):
    p=urlparse(url)
    if p.scheme!='https' or not p.hostname: raise HTTPException(422,'A imagem remota precisa usar HTTPS.')
    try:
        for info in socket.getaddrinfo(p.hostname,443,type=socket.SOCK_STREAM):
            ip=ipaddress.ip_address(info[4][0])
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast: raise HTTPException(422,'Host de imagem não permitido.')
    except HTTPException: raise
    except Exception: raise HTTPException(422,'Não foi possível validar o host da imagem.')

def _save_reference(db,p,c,pr,raw,filename,ctype,source_type,source_url=''):
    refs=db.scalars(select(ProductVisualReference).where(ProductVisualReference.campaign_id==c.id,ProductVisualReference.company_id==p.company_id).order_by(ProductVisualReference.position)).all()
    if len(refs)>=3: raise HTTPException(422,'A campanha já possui 3 imagens de referência. Remova uma para adicionar outra.')
    real_type,w,h=_inspect_image(raw,ctype); digest=hashlib.sha256(raw).hexdigest()
    duplicate=next((r for r in refs if r.sha256==digest),None)
    if duplicate:return duplicate
    pos=len(refs)+1; key=build_key(c.id,f'product-ref-{pos}-{filename or "image.jpg"}')
    put_bytes(key,raw,real_type)
    x=ProductVisualReference(company_id=p.company_id,campaign_id=c.id,product_id=pr.id,storage_key=key,filename=(filename or f'product-{pos}.jpg')[:500],content_type=real_type,size_bytes=len(raw),width=w,height=h,sha256=digest,source_type=source_type,source_url=source_url[:2000],is_primary=(len(refs)==0),position=pos,validated_at=datetime.utcnow())
    db.add(x);db.commit();db.refresh(x);return x

@router.get('/variants/{variant_id}/visual-references')
def visual_list(variant_id:int,p:Principal=Depends(require_role('EDITOR')),db:Session=Depends(get_db)):
    v,c,pr=ctx(db,p.company_id,variant_id);xs=db.scalars(select(ProductVisualReference).where(ProductVisualReference.campaign_id==c.id,ProductVisualReference.company_id==p.company_id).order_by(ProductVisualReference.position)).all()
    return {'product':{'id':pr.id,'title':pr.title,'marketplace':pr.marketplace,'external_id':pr.external_id,'image_url':pr.image_url},'references':[_visual_json(x) for x in xs],'ready':len(xs)>0,'recommended':len(xs)>=3}

@router.post('/variants/{variant_id}/visual-references/upload')
async def visual_upload(variant_id:int,file:UploadFile=File(...),p:Principal=Depends(require_role('EDITOR')),db:Session=Depends(get_db)):
    v,c,pr=ctx(db,p.company_id,variant_id);raw=await file.read(MAX_REFERENCE_BYTES+1);x=_save_reference(db,p,c,pr,raw,file.filename or 'image.jpg',file.content_type or '', 'upload');return _visual_json(x)

@router.post('/variants/{variant_id}/visual-references/import-product-image')
async def visual_import_product(variant_id:int,p:Principal=Depends(require_role('EDITOR')),db:Session=Depends(get_db)):
    v,c,pr=ctx(db,p.company_id,variant_id);url=(pr.image_url or '').strip()
    if not url: raise HTTPException(422,'O produto não possui imagem oficial cadastrada.')
    _assert_public_https(url)
    async with httpx.AsyncClient(timeout=25,follow_redirects=False) as client:
        r=await client.get(url,headers={'User-Agent':'AIAffiliateIntelligence/1.14'})
    if 300<=r.status_code<400: raise HTTPException(422,'A origem redirecionou a imagem. Atualize a imagem oficial do produto antes de importar.')
    if r.status_code>=400: raise HTTPException(502,f'Não foi possível obter a imagem oficial ({r.status_code}).')
    x=_save_reference(db,p,c,pr,r.content,'marketplace-product.jpg',r.headers.get('content-type','').split(';')[0], 'marketplace',url);return _visual_json(x)

@router.get('/variants/{variant_id}/visual-references/{reference_id}/content')
def visual_content(variant_id:int,reference_id:int,p:Principal=Depends(require_role('EDITOR')),db:Session=Depends(get_db)):
    v,c,pr=ctx(db,p.company_id,variant_id);x=db.scalar(select(ProductVisualReference).where(ProductVisualReference.id==reference_id,ProductVisualReference.campaign_id==c.id,ProductVisualReference.company_id==p.company_id))
    if not x: raise HTTPException(404,'Referência não encontrada.')
    from fastapi.responses import Response
    return Response(content=get_bytes(x.storage_key),media_type=x.content_type,headers={'Cache-Control':'private, max-age=300'})

@router.put('/variants/{variant_id}/visual-references/{reference_id}/primary')
def visual_primary(variant_id:int,reference_id:int,p:Principal=Depends(require_role('EDITOR')),db:Session=Depends(get_db)):
    v,c,pr=ctx(db,p.company_id,variant_id);xs=db.scalars(select(ProductVisualReference).where(ProductVisualReference.campaign_id==c.id,ProductVisualReference.company_id==p.company_id)).all();target=next((x for x in xs if x.id==reference_id),None)
    if not target: raise HTTPException(404,'Referência não encontrada.')
    for x in xs:x.is_primary=(x.id==reference_id)
    db.commit();return {'ok':True}

@router.delete('/variants/{variant_id}/visual-references/{reference_id}')
def visual_delete(variant_id:int,reference_id:int,p:Principal=Depends(require_role('EDITOR')),db:Session=Depends(get_db)):
    v,c,pr=ctx(db,p.company_id,variant_id);x=db.scalar(select(ProductVisualReference).where(ProductVisualReference.id==reference_id,ProductVisualReference.campaign_id==c.id,ProductVisualReference.company_id==p.company_id))
    if not x: raise HTTPException(404,'Referência não encontrada.')
    old=x.storage_key;was=x.is_primary;db.delete(x);db.commit();delete_media(old)
    if was:
        nxt=db.scalar(select(ProductVisualReference).where(ProductVisualReference.campaign_id==c.id,ProductVisualReference.company_id==p.company_id).order_by(ProductVisualReference.position))
        if nxt:nxt.is_primary=True;db.commit()
    return {'ok':True}

@router.get('/status')
def configured(p:Principal=Depends(require_role('EDITOR'))):
    from app.core.config import settings
    return {'configured':bool(settings.openai_api_key),'text_model':settings.openai_text_model,'video_configured':bool(settings.fal_key),'video_provider':settings.video_provider,'video_model':settings.fal_video_model}
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
    refs=db.scalars(select(ProductVisualReference).where(ProductVisualReference.campaign_id==c.id,ProductVisualReference.company_id==p.company_id).order_by(ProductVisualReference.is_primary.desc(),ProductVisualReference.position)).all()
    if not refs: raise HTTPException(422,'Adicione ao menos uma imagem real do produto antes de gerar vídeo com IA. Recomendamos 3 referências.')
    signed=[presigned_get_url(r.storage_key,1800) for r in refs[:3]]
    safety=f'''Vertical 9:16 commercial for the REAL product shown in @Element1 / reference images. Product: {pr.title}. Preserve the exact package silhouette, colors, brand identity, variant and visible label. Do not redesign packaging, invent a different package, replace logo, change product weight/variant, or invent readable label text. Keep the real product visually consistent; move camera/background rather than changing the product. No invented claims or prices.'''
    prompt=(x.prompt.strip()+"\n"+safety).strip() if x.prompt.strip() else safety
    d=await start_video(prompt,x.seconds,signed)
    if not usage:
        usage=UsageCounter(company_id=p.company_id,period_key=key)
        db.add(usage)
    # Não consome franquia ao apenas enfileirar. A cobrança ocorre somente após conclusão/anexo.
    db.commit()
    return {'variant_id':v.id,'video_id':d.get('id'),'status':d.get('status'),'progress':d.get('progress',0),'seconds':d.get('seconds'),'provider':d.get('provider'),'model':d.get('model'),'status_url':d.get('status_url'),'response_url':d.get('response_url'),'usage':{'used':used,'limit':limit}}
@router.post('/video/status')
async def poll(x:StatusIn,p:Principal=Depends(require_role('EDITOR')),db:Session=Depends(get_db)):
    v,c,pr=ctx(db,p.company_id,x.variant_id);d=await video_status(x.video_id,x.status_url or None);status=d.get('status','')
    if status=='completed':
        # Evita cobrar novamente caso o frontend repita o polling após o mesmo job já ter sido anexado.
        job_marker=f'ai-video-{x.video_id}.mp4'
        already_attached=(v.media_filename==job_marker)
        if not already_attached:
            raw=await download_video(x.video_id,x.response_url or None);old=v.media_storage_key;key=build_key(v.id,job_marker);put_bytes(key,raw,'video/mp4');v.media_storage_key=key;v.media_filename=job_marker;v.media_content_type='video/mp4';v.media_size=len(raw);v.media_duration_seconds=int(d.get('seconds') or 0);v.media_url=''
            period=datetime.utcnow().strftime('%Y-%m');usage=db.scalar(select(UsageCounter).where(UsageCounter.company_id==p.company_id,UsageCounter.period_key==period))
            if not usage: usage=UsageCounter(company_id=p.company_id,period_key=period);db.add(usage)
            usage.ai_video_generations=int(getattr(usage,'ai_video_generations',0) or 0)+1
            db.commit();delete_media(old)
    err=d.get('error') or {};return {'variant_id':v.id,'video_id':x.video_id,'status':status,'progress':d.get('progress',0),'error':err.get('message') if isinstance(err,dict) else str(err or ''),'attached':bool(v.media_storage_key)}
