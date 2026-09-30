from datetime import datetime, timedelta
import secrets
from urllib.parse import urlencode
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.db import get_db
from app.models.entities import Product
from app.models.social import SocialConnection, SocialOAuthAttempt, ContentCampaign, ContentVariant, Publication
from app.routers.mercadolivre import require_admin
from app.services.social_crypto import encrypt
from app.services.social_publishers import publish, PublishError

router=APIRouter(prefix='/api/v1/social',tags=['social'])
PLATFORMS=['Instagram','TikTok','YouTube Shorts','Pinterest']

class CampaignRequest(BaseModel):
    product_id:int
    platforms:list[str]
    objective:str='Venda'
    format:str='Vídeo curto'
    duration_seconds:int=30
    tone:str='Direto e acessível'
    audience:str=''
class ApprovalRequest(BaseModel): approved:bool=True
class ScheduleRequest(BaseModel): scheduled_at:datetime|None=None
class MediaRequest(BaseModel): media_url:str

def _variant(p:Product, platform:str, duration:int, tone:str, audience:str):
    target=f' para {audience}' if audience.strip() else ''
    hooks={
      'TikTok':f'Vale a pena conhecer {p.title[:70]}?',
      'Instagram':f'Olha este achado: {p.title[:75]}',
      'YouTube Shorts':f'{p.title[:70]} em {duration} segundos',
      'Pinterest':f'Ideia para salvar: {p.title[:75]}' }
    hook=hooks.get(platform,f'Conheça {p.title[:80]}')
    cta='Confira preço, disponibilidade e condições atualizadas no link de afiliado.'
    tags='#achadinhos #ofertas #comprasonline #publicidade'
    caption=f'{hook}\n\n{p.title}\n{cta}\n{p.affiliate_url}\n\n{tags}\n\nPublicidade • Link de afiliado: posso receber comissão por compras qualificadas.'
    script=(f'0–3s — GANCHO: {hook}\n3–{max(7,duration-8)}s — Mostre o produto e somente características verificadas no anúncio oficial{target}. '
            f'Não prometa resultados não comprovados.\n{max(8,duration-7)}–{duration}s — CTA: {cta}\nTom: {tone}. Inclua identificação de publicidade.')
    return hook,caption,script,tags,cta

@router.get('/products',dependencies=[Depends(require_admin)])
def products(db:Session=Depends(get_db)):
    rows=db.scalars(select(Product).where(Product.affiliate_url!='').order_by(Product.id.desc()).limit(200)).all()
    return [{'id':p.id,'title':p.title,'image_url':p.image_url,'marketplace':p.marketplace,'price':p.price,'affiliate_url':p.affiliate_url} for p in rows]

@router.post('/campaigns',dependencies=[Depends(require_admin)])
def create_campaign(data:CampaignRequest,db:Session=Depends(get_db)):
    p=db.get(Product,data.product_id)
    if not p: raise HTTPException(404,'Produto não encontrado')
    if not p.affiliate_url: raise HTTPException(409,'Produto sem link de afiliado')
    platforms=list(dict.fromkeys(data.platforms))
    if not platforms or any(x not in PLATFORMS for x in platforms): raise HTTPException(422,'Selecione ao menos uma rede válida')
    if data.duration_seconds not in (15,30,60): raise HTTPException(422,'Duração deve ser 15, 30 ou 60 segundos')
    c=ContentCampaign(product_id=p.id,name=p.title[:300],objective=data.objective,format=data.format,duration_seconds=data.duration_seconds,tone=data.tone,audience=data.audience,status='draft')
    db.add(c);db.flush()
    variants=[]
    for platform in platforms:
        hook,caption,script,tags,cta=_variant(p,platform,data.duration_seconds,data.tone,data.audience)
        v=ContentVariant(campaign_id=c.id,platform=platform,title=p.title[:300],hook=hook,caption=caption,script=script,hashtags=tags,cta=cta,status='draft')
        db.add(v);db.flush();variants.append(v)
    db.commit()
    return campaign_detail(c.id,db)

@router.get('/campaigns',dependencies=[Depends(require_admin)])
def campaigns(db:Session=Depends(get_db)):
    rows=db.scalars(select(ContentCampaign).order_by(ContentCampaign.id.desc()).limit(100)).all()
    return [{'id':c.id,'product_id':c.product_id,'name':c.name,'objective':c.objective,'format':c.format,'duration_seconds':c.duration_seconds,'status':c.status,'created_at':c.created_at.isoformat()} for c in rows]

@router.get('/campaigns/{campaign_id}',dependencies=[Depends(require_admin)])
def campaign_detail(campaign_id:int,db:Session=Depends(get_db)):
    c=db.get(ContentCampaign,campaign_id)
    if not c: raise HTTPException(404,'Campanha não encontrada')
    vs=db.scalars(select(ContentVariant).where(ContentVariant.campaign_id==c.id).order_by(ContentVariant.id)).all()
    pubs=db.scalars(select(Publication).where(Publication.campaign_id==c.id).order_by(Publication.id.desc())).all()
    return {'id':c.id,'product_id':c.product_id,'name':c.name,'objective':c.objective,'format':c.format,'duration_seconds':c.duration_seconds,'tone':c.tone,'audience':c.audience,'status':c.status,
      'variants':[{'id':v.id,'platform':v.platform,'title':v.title,'hook':v.hook,'caption':v.caption,'script':v.script,'hashtags':v.hashtags,'cta':v.cta,'media_url':v.media_url,'status':v.status} for v in vs],
      'publications':[{'id':x.id,'variant_id':x.variant_id,'platform':x.platform,'status':x.status,'scheduled_at':x.scheduled_at.isoformat() if x.scheduled_at else None,'published_at':x.published_at.isoformat() if x.published_at else None,'external_post_id':x.external_post_id,'external_post_url':x.external_post_url,'error_message':x.error_message,'retry_count':x.retry_count} for x in pubs]}

@router.post('/campaigns/{campaign_id}/approve',dependencies=[Depends(require_admin)])
def approve(campaign_id:int,data:ApprovalRequest,db:Session=Depends(get_db)):
    c=db.get(ContentCampaign,campaign_id)
    if not c: raise HTTPException(404,'Campanha não encontrada')
    c.status='approved' if data.approved else 'draft'
    for v in db.scalars(select(ContentVariant).where(ContentVariant.campaign_id==c.id)).all(): v.status=c.status
    db.commit();return {'id':c.id,'status':c.status}

@router.post('/variants/{variant_id}/media',dependencies=[Depends(require_admin)])
def set_media(variant_id:int,data:MediaRequest,db:Session=Depends(get_db)):
    v=db.get(ContentVariant,variant_id)
    if not v: raise HTTPException(404,'Variação não encontrada')
    if data.media_url and not data.media_url.lower().startswith('https://'): raise HTTPException(422,'Use uma URL HTTPS pública para a mídia')
    v.media_url=data.media_url.strip();db.commit();return {'id':v.id,'media_url':v.media_url}

@router.post('/campaigns/{campaign_id}/schedule',dependencies=[Depends(require_admin)])
def schedule(campaign_id:int,data:ScheduleRequest,db:Session=Depends(get_db)):
    c=db.get(ContentCampaign,campaign_id)
    if not c: raise HTTPException(404,'Campanha não encontrada')
    if c.status!='approved': raise HTTPException(409,'Aprove a campanha antes de agendar/publicar')
    vs=db.scalars(select(ContentVariant).where(ContentVariant.campaign_id==c.id)).all()
    created=[]
    for v in vs:
        pub=Publication(campaign_id=c.id,variant_id=v.id,platform=v.platform,status='scheduled' if data.scheduled_at else 'queued',scheduled_at=data.scheduled_at)
        db.add(pub);db.flush();created.append(pub.id)
    c.status='scheduled' if data.scheduled_at else 'queued';db.commit()
    return {'campaign_id':c.id,'publication_ids':created,'status':c.status}

async def _execute(pub:Publication,db:Session):
    v=db.get(ContentVariant,pub.variant_id)
    conn=db.scalar(select(SocialConnection).where(SocialConnection.platform==pub.platform))
    pub.status='publishing';db.commit()
    try:
        result=await publish(pub.platform,conn,v)
        pub.status='published';pub.published_at=datetime.utcnow();pub.external_post_id=result.get('external_post_id','');pub.external_post_url=result.get('external_post_url','');pub.error_message=''
    except Exception as e:
        pub.status='error';pub.error_message=str(e)[:4000];pub.retry_count+=1
    db.commit()

@router.post('/publications/{publication_id}/run',dependencies=[Depends(require_admin)])
async def run_publication(publication_id:int,db:Session=Depends(get_db)):
    pub=db.get(Publication,publication_id)
    if not pub: raise HTTPException(404,'Publicação não encontrada')
    await _execute(pub,db);return {'id':pub.id,'status':pub.status,'error_message':pub.error_message,'external_post_id':pub.external_post_id}

@router.get('/connections',dependencies=[Depends(require_admin)])
def connections(db:Session=Depends(get_db)):
    found={x.platform:x for x in db.scalars(select(SocialConnection)).all()}
    config={'TikTok':bool(settings.tiktok_client_key and settings.tiktok_client_secret and settings.tiktok_redirect_uri),'Instagram':bool(settings.meta_app_id and settings.meta_app_secret and settings.meta_redirect_uri),'YouTube Shorts':bool(settings.youtube_client_id and settings.youtube_client_secret and settings.youtube_redirect_uri),'Pinterest':bool(settings.pinterest_client_id and settings.pinterest_client_secret and settings.pinterest_redirect_uri)}
    return [{'platform':p,'configured':config[p],'connected':p in found,'account_name':found[p].account_name if p in found else '','expires_at':found[p].expires_at.isoformat() if p in found and found[p].expires_at else None} for p in PLATFORMS]

@router.post('/tiktok/authorize',dependencies=[Depends(require_admin)])
def tiktok_authorize(db:Session=Depends(get_db)):
    if not(settings.tiktok_client_key and settings.tiktok_client_secret and settings.tiktok_redirect_uri): raise HTTPException(409,'Configure TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET e TIKTOK_REDIRECT_URI')
    state=secrets.token_urlsafe(32);db.add(SocialOAuthAttempt(platform='TikTok',state=state));db.commit()
    params={'client_key':settings.tiktok_client_key,'response_type':'code','scope':'user.info.basic,video.publish','redirect_uri':settings.tiktok_redirect_uri,'state':state}
    return {'authorization_url':'https://www.tiktok.com/v2/auth/authorize/?'+urlencode(params)}

@router.get('/tiktok/callback')
async def tiktok_callback(code:str=Query(''),state:str=Query(''),error:str=Query(''),db:Session=Depends(get_db)):
    if error: return RedirectResponse(settings.frontend_url+'/integracoes?social_error='+error)
    attempt=db.scalar(select(SocialOAuthAttempt).where(SocialOAuthAttempt.platform=='TikTok',SocialOAuthAttempt.state==state))
    if not attempt or not code: raise HTTPException(400,'Callback TikTok inválido ou state expirado')
    if datetime.utcnow()-attempt.created_at>timedelta(minutes=15): raise HTTPException(400,'State expirado')
    form={'client_key':settings.tiktok_client_key,'client_secret':settings.tiktok_client_secret,'code':code,'grant_type':'authorization_code','redirect_uri':settings.tiktok_redirect_uri}
    async with httpx.AsyncClient(timeout=30) as client:r=await client.post('https://open.tiktokapis.com/v2/oauth/token/',data=form,headers={'Content-Type':'application/x-www-form-urlencoded'})
    data=r.json()
    if r.status_code>=400 or not data.get('access_token'): raise HTTPException(502,f'Falha ao conectar TikTok: {data}')
    conn=db.scalar(select(SocialConnection).where(SocialConnection.platform=='TikTok')) or SocialConnection(platform='TikTok')
    conn.external_user_id=data.get('open_id','');conn.account_name='TikTok';conn.access_token_enc=encrypt(data['access_token']);conn.refresh_token_enc=encrypt(data.get('refresh_token',''));conn.scopes=data.get('scope','');conn.expires_at=datetime.utcnow()+timedelta(seconds=int(data.get('expires_in',86400)));conn.connected_at=datetime.utcnow()
    db.add(conn);db.delete(attempt);db.commit()
    return RedirectResponse(settings.frontend_url+'/integracoes?social_connected=tiktok',status_code=303)

@router.delete('/connections/{platform}',dependencies=[Depends(require_admin)])
def disconnect(platform:str,db:Session=Depends(get_db)):
    conn=db.scalar(select(SocialConnection).where(SocialConnection.platform==platform))
    if conn: db.delete(conn);db.commit()
    return {'connected':False,'platform':platform}
