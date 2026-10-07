from datetime import datetime, timedelta
import secrets
import re
from urllib.parse import urlencode
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import RedirectResponse, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.db import get_db
from app.models.entities import Product
from app.models.saas import GrowthEvent
from app.services.plan_limits import enforce_monthly_limit, consume
from app.models.social import SocialConnection, SocialOAuthAttempt, ContentCampaign, ContentVariant, Publication, ProductVisualReference
from app.core.auth import current_principal, require_role, Principal
from app.services.social_crypto import encrypt
from app.services.social_publishers import publish, PublishError, tiktok_creator_info, fetch_tiktok_status, pinterest_boards
from app.services.media_storage import build_key, put_bytes, get_bytes, delete as delete_media, MediaStorageError, presigned_get_url

router=APIRouter(prefix='/api/v1/social',tags=['social'])
PLATFORMS=['Instagram','TikTok','YouTube Shorts','Pinterest']
VIDEO_TYPES={'video/mp4','video/quicktime','video/webm'}

class CampaignRequest(BaseModel):
    product_id:int; platforms:list[str]; objective:str='Venda'; format:str='Vídeo curto'; duration_seconds:int=30; tone:str='Direto e acessível'; audience:str=''
class ApprovalRequest(BaseModel): approved:bool=True
class ScheduleRequest(BaseModel):
    scheduled_at:datetime|None=None
    tiktok_privacy_level:str='SELF_ONLY'
    tiktok_disable_comment:bool=False
    tiktok_disable_duet:bool=False
    tiktok_disable_stitch:bool=False
    tiktok_user_consent:bool=False
    tiktok_brand_content:bool=False
    tiktok_brand_organic:bool=False
    tiktok_is_aigc:bool=False
    pinterest_board_id:str=''
    pinterest_board_name:str=''
class AffiliateLinkRequest(BaseModel):
    affiliate_url:str
    affiliate_label:str=''
    link_placement:str='bio'
class MediaRequest(BaseModel): media_url:str

def _variant(p:Product, platform:str, duration:int, tone:str, audience:str):
    target=f' para {audience}' if audience.strip() else ''
    hooks={'TikTok':f'Vale a pena conhecer {p.title[:70]}?','Instagram':f'Olha este achado: {p.title[:75]}','YouTube Shorts':f'{p.title[:70]} em {duration} segundos','Pinterest':f'Ideia para salvar: {p.title[:75]}'}
    hook=hooks.get(platform,f'Conheça {p.title[:80]}')
    if platform=='TikTok':
        cta='Confira o produto pelo link indicado no perfil.'
        link_line=''
    else:
        cta='Confira preço, disponibilidade e condições atualizadas no link de afiliado.'
        link_line=f'\n{p.affiliate_url}' if p.affiliate_url else ''
    tags='#achadinhos #ofertas #comprasonline #publicidade'
    caption=f'{hook}\n\n{p.title}\n{cta}{link_line}\n\n{tags}\n\nPublicidade • Posso receber comissão por compras qualificadas.'
    script=(f'0–3s — GANCHO: {hook}\n3–{max(7,duration-8)}s — Mostre o produto e somente características verificadas no anúncio oficial{target}. '
            f'Não prometa resultados não comprovados.\n{max(8,duration-7)}–{duration}s — CTA: {cta}\nTom: {tone}. Inclua identificação de publicidade.')
    return hook,caption,script,tags,cta

def _variant_json(v:ContentVariant):
    return {'id':v.id,'platform':v.platform,'title':v.title,'hook':v.hook,'caption':v.caption,'script':v.script,'hashtags':v.hashtags,'cta':v.cta,
      'media_url':v.media_url,'media_filename':v.media_filename,'media_content_type':v.media_content_type,'media_size':v.media_size,'media_duration_seconds':v.media_duration_seconds,'has_uploaded_media':bool(v.media_storage_key),'affiliate_url':v.affiliate_url,'affiliate_label':v.affiliate_label,'link_placement':v.link_placement,'affiliate_configured':bool(v.affiliate_configured_at),'affiliate_configured_at':v.affiliate_configured_at.isoformat() if v.affiliate_configured_at else None,'status':v.status}

def _publication_json(x:Publication):
    return {'id':x.id,'variant_id':x.variant_id,'platform':x.platform,'status':x.status,'scheduled_at':x.scheduled_at.isoformat() if x.scheduled_at else None,
      'published_at':x.published_at.isoformat() if x.published_at else None,'external_post_id':x.external_post_id,'external_post_url':x.external_post_url,'error_message':x.error_message,'retry_count':x.retry_count,'privacy_level':x.privacy_level,'brand_content_toggle':x.brand_content_toggle,'brand_organic_toggle':x.brand_organic_toggle,'is_aigc':x.is_aigc,'tiktok_status':x.tiktok_status,'tiktok_fail_reason':x.tiktok_fail_reason,'uploaded_bytes':x.uploaded_bytes,'public_post_ids':x.public_post_ids,'pinterest_board_id':x.pinterest_board_id,'pinterest_board_name':x.pinterest_board_name}

@router.get('/products')
def products(p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    rows=db.scalars(select(Product).where(Product.company_id==p.company_id,Product.affiliate_url!='').order_by(Product.id.desc()).limit(200)).all()
    return [{'id':p.id,'title':p.title,'image_url':p.image_url,'marketplace':p.marketplace,'price':p.price,'affiliate_url':p.affiliate_url} for p in rows]

@router.post('/campaigns')
def create_campaign(data:CampaignRequest,p:Principal=Depends(require_role('EDITOR')),db:Session=Depends(get_db)):
    usage,_,_=enforce_monthly_limit(db,p.company_id,'campaigns_month','campaigns_created',1)
    product=db.scalar(select(Product).where(Product.id==data.product_id,Product.company_id==p.company_id))
    if not product: raise HTTPException(404,'Produto não encontrado')
    if not product.affiliate_url: raise HTTPException(409,'Produto sem link de afiliado')
    platforms=list(dict.fromkeys(data.platforms))
    if not platforms or any(x not in PLATFORMS for x in platforms): raise HTTPException(422,'Selecione ao menos uma rede válida')
    if data.duration_seconds not in (15,30,60): raise HTTPException(422,'Duração deve ser 15, 30 ou 60 segundos')
    c=ContentCampaign(company_id=p.company_id,product_id=product.id,name=product.title[:300],objective=data.objective,format=data.format,duration_seconds=data.duration_seconds,tone=data.tone,audience=data.audience,status='draft')
    db.add(c);db.flush()
    for platform in platforms:
        hook,caption,script,tags,cta=_variant(product,platform,data.duration_seconds,data.tone,data.audience)
        db.add(ContentVariant(company_id=p.company_id,campaign_id=c.id,platform=platform,title=product.title[:300],hook=hook,caption=caption,script=script,hashtags=tags,cta=cta,affiliate_url=product.affiliate_url,affiliate_label=product.affiliate_label,link_placement='bio' if platform=='TikTok' else 'caption',status='draft'))
    consume(usage,'campaigns_created',1)
    db.commit();return {'id':c.id,'product_id':c.product_id,'name':c.name,'objective':c.objective,'format':c.format,'duration_seconds':c.duration_seconds,'tone':c.tone,'audience':c.audience,'status':c.status,'variants':[_variant_json(v) for v in db.scalars(select(ContentVariant).where(ContentVariant.company_id==p.company_id,ContentVariant.campaign_id==c.id)).all()],'publications':[]}

@router.get('/campaigns')
def campaigns(p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    rows=db.scalars(select(ContentCampaign).where(ContentCampaign.company_id==p.company_id).order_by(ContentCampaign.id.desc()).limit(100)).all()
    return [{'id':c.id,'product_id':c.product_id,'name':c.name,'objective':c.objective,'format':c.format,'duration_seconds':c.duration_seconds,'status':c.status,'created_at':c.created_at.isoformat()} for c in rows]

@router.get('/campaigns/{campaign_id}')
def campaign_detail(campaign_id:int,p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    c=db.scalar(select(ContentCampaign).where(ContentCampaign.id==campaign_id,ContentCampaign.company_id==p.company_id))
    if not c: raise HTTPException(404,'Campanha não encontrada')
    vs=db.scalars(select(ContentVariant).where(ContentVariant.company_id==p.company_id,ContentVariant.campaign_id==c.id).order_by(ContentVariant.id)).all()
    pubs=db.scalars(select(Publication).where(Publication.company_id==p.company_id,Publication.campaign_id==c.id).order_by(Publication.id.desc())).all()
    return {'id':c.id,'product_id':c.product_id,'name':c.name,'objective':c.objective,'format':c.format,'duration_seconds':c.duration_seconds,'tone':c.tone,'audience':c.audience,'status':c.status,'variants':[_variant_json(v) for v in vs],'publications':[_publication_json(x) for x in pubs]}

@router.post('/campaigns/{campaign_id}/approve')
def approve(campaign_id:int,data:ApprovalRequest,p:Principal=Depends(require_role('EDITOR')),db:Session=Depends(get_db)):
    c=db.scalar(select(ContentCampaign).where(ContentCampaign.id==campaign_id,ContentCampaign.company_id==p.company_id))
    if not c: raise HTTPException(404,'Campanha não encontrada')
    if data.approved:
        variants=db.scalars(select(ContentVariant).where(ContentVariant.company_id==p.company_id,ContentVariant.campaign_id==c.id)).all()
        if any((v.media_filename or '').startswith('ai-video-') for v in variants):
            refs=db.scalars(select(ProductVisualReference).where(ProductVisualReference.company_id==p.company_id,ProductVisualReference.campaign_id==c.id)).all()
            if not refs: raise HTTPException(409,'Vídeo gerado por IA sem referência visual real do produto. Adicione uma foto real antes de aprovar.')
    c.status='approved' if data.approved else 'draft'
    for v in db.scalars(select(ContentVariant).where(ContentVariant.company_id==p.company_id,ContentVariant.campaign_id==c.id)).all():v.status=c.status
    db.commit();return {'id':c.id,'status':c.status}

@router.post('/variants/{variant_id}/media')
def set_media_url(variant_id:int,data:MediaRequest,p:Principal=Depends(require_role('EDITOR')),db:Session=Depends(get_db)):
    v=db.scalar(select(ContentVariant).where(ContentVariant.id==variant_id,ContentVariant.company_id==p.company_id))
    if not v: raise HTTPException(404,'Variação não encontrada')
    if data.media_url and not data.media_url.lower().startswith('https://'):raise HTTPException(422,'Use uma URL HTTPS pública para a mídia')
    v.media_url=data.media_url.strip();db.commit();return _variant_json(v)

@router.post('/variants/{variant_id}/media/upload')
async def upload_media(variant_id:int,file:UploadFile=File(...),duration_seconds:int=Form(0),p:Principal=Depends(require_role('EDITOR')),db:Session=Depends(get_db)):
    v=db.scalar(select(ContentVariant).where(ContentVariant.id==variant_id,ContentVariant.company_id==p.company_id))
    if not v:raise HTTPException(404,'Variação não encontrada')
    ctype=(file.content_type or '').lower()
    if ctype not in VIDEO_TYPES:raise HTTPException(422,'Use vídeo MP4, MOV ou WebM.')
    max_bytes=settings.media_max_upload_mb*1024*1024
    data=await file.read(max_bytes+1)
    if not data:raise HTTPException(422,'Arquivo vazio.')
    if len(data)>max_bytes:raise HTTPException(413,f'Arquivo excede {settings.media_max_upload_mb} MB.')
    old=v.media_storage_key;key=build_key(v.id,file.filename or 'video.mp4')
    try:put_bytes(key,data,ctype)
    except MediaStorageError as e:raise HTTPException(503,str(e))
    v.media_storage_key=key;v.media_filename=(file.filename or 'video.mp4')[:500];v.media_content_type=ctype;v.media_size=len(data);v.media_duration_seconds=max(0,duration_seconds);v.media_url=''
    campaign=db.scalar(select(ContentCampaign).where(ContentCampaign.id==v.campaign_id,ContentCampaign.company_id==p.company_id))
    if campaign and duration_seconds>0: campaign.duration_seconds=duration_seconds
    db.commit();delete_media(old);return _variant_json(v)

@router.get('/variants/{variant_id}/media/content')
def media_content(variant_id:int,p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    v=db.scalar(select(ContentVariant).where(ContentVariant.id==variant_id,ContentVariant.company_id==p.company_id))
    if not v:raise HTTPException(404,'Variação não encontrada')
    if not v.media_storage_key:raise HTTPException(404,'Vídeo não encontrado')
    try:data=get_bytes(v.media_storage_key)
    except MediaStorageError as exc:raise HTTPException(502,str(exc))
    headers={'Content-Disposition':f'inline; filename="{(v.media_filename or "video.mp4").replace(chr(34), "")}"','Cache-Control':'private, max-age=300'}
    return Response(content=data,media_type=v.media_content_type or 'video/mp4',headers=headers)

@router.delete('/variants/{variant_id}/media')
def remove_media(variant_id:int,p:Principal=Depends(require_role('EDITOR')),db:Session=Depends(get_db)):
    v=db.scalar(select(ContentVariant).where(ContentVariant.id==variant_id,ContentVariant.company_id==p.company_id))
    if not v:raise HTTPException(404,'Variação não encontrada')
    old=v.media_storage_key;v.media_storage_key='';v.media_filename='';v.media_content_type='';v.media_size=0;v.media_duration_seconds=0;v.media_url='';db.commit();delete_media(old)
    return _variant_json(v)

@router.put('/variants/{variant_id}/affiliate-link')
def update_affiliate_link(variant_id:int,data:AffiliateLinkRequest,p:Principal=Depends(require_role('EDITOR')),db:Session=Depends(get_db)):
    v=db.scalar(select(ContentVariant).where(ContentVariant.id==variant_id,ContentVariant.company_id==p.company_id))
    if not v:raise HTTPException(404,'Variação não encontrada')
    url=data.affiliate_url.strip()
    label=data.affiliate_label.strip()
    if label and (len(label)>30 or not re.fullmatch(r'[a-z0-9]+',label)):
        raise HTTPException(422,'Etiqueta do Mercado Livre: use até 30 caracteres, somente letras minúsculas e números, sem espaços.')
    if url and not url.lower().startswith('https://'):raise HTTPException(422,'Use um link HTTPS oficial de afiliado.')
    placement=data.link_placement if data.link_placement in ('bio','caption','description','manual') else 'manual'
    v.affiliate_url=url;v.affiliate_label=label;v.link_placement=placement;v.affiliate_configured_at=datetime.utcnow()
    db.commit();db.refresh(v);return _variant_json(v)

@router.get('/tiktok/creator-info')
async def creator_info(p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    conn=db.scalar(select(SocialConnection).where(SocialConnection.company_id==p.company_id,SocialConnection.platform=='TikTok'))
    if not conn:raise HTTPException(409,'Conecte o TikTok em Integrações.')
    try:return await tiktok_creator_info(conn)
    except PublishError as e:raise HTTPException(502,str(e))

@router.post('/campaigns/{campaign_id}/schedule')
async def schedule(campaign_id:int,data:ScheduleRequest,p:Principal=Depends(require_role('EDITOR')),db:Session=Depends(get_db)):
    c=db.scalar(select(ContentCampaign).where(ContentCampaign.id==campaign_id,ContentCampaign.company_id==p.company_id))
    if not c:raise HTTPException(404,'Campanha não encontrada')
    if c.status!='approved':raise HTTPException(409,'Aprove a campanha antes de agendar/publicar')
    vs=db.scalars(select(ContentVariant).where(ContentVariant.company_id==p.company_id,ContentVariant.campaign_id==c.id)).all()
    not_configured=[v.platform for v in vs if not v.affiliate_configured_at]
    if not_configured: raise HTTPException(409,f"Salve a configuração de link antes de publicar: {', '.join(not_configured)}")
    if any(v.platform=='TikTok' for v in vs):
        if not data.tiktok_user_consent:raise HTTPException(422,'Confirme o consentimento antes de enviar ao TikTok.')
        conn=db.scalar(select(SocialConnection).where(SocialConnection.company_id==p.company_id,SocialConnection.platform=='TikTok'))
        if not conn:raise HTTPException(409,'Conecte o TikTok em Integrações.')
        try:info=await tiktok_creator_info(conn)
        except PublishError as e:raise HTTPException(502,str(e))
        if data.tiktok_privacy_level not in (info.get('privacy_level_options') or []):raise HTTPException(422,'Privacidade não disponível para esta conta TikTok.')
        if data.tiktok_brand_content and data.tiktok_privacy_level=='SELF_ONLY':raise HTTPException(422,'TikTok não permite Branded Content com visibilidade Somente eu. Use uma opção de privacidade compatível quando o app estiver auditado.')
    if any(v.platform=='Pinterest' for v in vs) and not data.pinterest_board_id.strip():
        raise HTTPException(422,'Selecione o board do Pinterest antes de publicar.')
    usage,_,_=enforce_monthly_limit(db,p.company_id,'publications_month','publications_created',len(vs))
    created=[]
    for v in vs:
        if v.platform=='TikTok' and not v.media_storage_key:raise HTTPException(422,'Adicione um vídeo à variação TikTok antes de colocar na fila.')
        pub=Publication(company_id=p.company_id,campaign_id=c.id,variant_id=v.id,platform=v.platform,status='scheduled' if data.scheduled_at else 'queued',scheduled_at=data.scheduled_at,
          privacy_level=data.tiktok_privacy_level,disable_comment=data.tiktok_disable_comment,disable_duet=data.tiktok_disable_duet,disable_stitch=data.tiktok_disable_stitch,user_consent=data.tiktok_user_consent,brand_content_toggle=data.tiktok_brand_content,brand_organic_toggle=data.tiktok_brand_organic,is_aigc=data.tiktok_is_aigc,pinterest_board_id=data.pinterest_board_id.strip() if v.platform=='Pinterest' else '',pinterest_board_name=data.pinterest_board_name.strip() if v.platform=='Pinterest' else '')
        if v.platform=='Pinterest':
            ref=db.scalar(select(ProductVisualReference).where(ProductVisualReference.company_id==p.company_id,ProductVisualReference.campaign_id==c.id).order_by(ProductVisualReference.is_primary.desc(),ProductVisualReference.position.asc()))
            if ref and ref.storage_key:
                try: pub.pinterest_cover_url=presigned_get_url(ref.storage_key,3600)
                except MediaStorageError: pub.pinterest_cover_url=''
            if not pub.pinterest_cover_url:
                product=db.get(Product,c.product_id);pub.pinterest_cover_url=(product.image_url if product else '') or ''
            if not pub.pinterest_cover_url: raise HTTPException(422,'Pinterest exige uma imagem de capa/referência real do produto.')
        db.add(pub);db.flush();created.append(pub.id)
    consume(usage,'publications_created',len(created))
    c.status='scheduled' if data.scheduled_at else 'queued';db.commit();return {'campaign_id':c.id,'publication_ids':created,'status':c.status}

async def _execute(pub:Publication,db:Session):
    v=db.get(ContentVariant,pub.variant_id);conn=db.scalar(select(SocialConnection).where(SocialConnection.company_id==pub.company_id,SocialConnection.platform==pub.platform));pub.status='publishing';pub.error_message='';db.commit()
    try:
        result=await publish(pub.platform,conn,v,pub);pub.status=result.get('status','processing');pub.external_post_id=result.get('external_post_id','');pub.external_post_url=result.get('external_post_url','')
        if pub.status=='published': pub.published_at=datetime.utcnow()
    except Exception as e:
        pub.status='error';pub.error_message=str(e)[:4000];pub.retry_count+=1
    db.commit()

@router.post('/publications/{publication_id}/run')
async def run_publication(publication_id:int,p:Principal=Depends(require_role('EDITOR')),db:Session=Depends(get_db)):
    pub=db.scalar(select(Publication).where(Publication.id==publication_id,Publication.company_id==p.company_id))
    if not pub:raise HTTPException(404,'Publicação não encontrada')
    await _execute(pub,db);return _publication_json(pub)

@router.post('/publications/{publication_id}/status')
async def publication_status(publication_id:int,p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    pub=db.scalar(select(Publication).where(Publication.id==publication_id,Publication.company_id==p.company_id))
    if not pub:raise HTTPException(404,'Publicação não encontrada')
    if pub.platform!='TikTok' or not pub.external_post_id:raise HTTPException(409,'Publicação ainda não possui publish_id do TikTok.')
    conn=db.scalar(select(SocialConnection).where(SocialConnection.company_id==p.company_id,SocialConnection.platform=='TikTok'))
    if not conn:raise HTTPException(409,'TikTok desconectado.')
    try:data=await fetch_tiktok_status(conn,pub.external_post_id)
    except PublishError as e:raise HTTPException(502,str(e))
    status=data.get('status','')
    pub.tiktok_status=status
    pub.tiktok_fail_reason=data.get('fail_reason') or ''
    pub.uploaded_bytes=int(data.get('uploaded_bytes') or 0)
    ids=data.get('publicaly_available_post_id') or data.get('publicly_available_post_id') or []
    if not isinstance(ids,list): ids=[ids] if ids else []
    pub.public_post_ids=','.join(str(x) for x in ids)
    if status=='PUBLISH_COMPLETE':
        pub.status='published';pub.published_at=datetime.utcnow();pub.error_message=''
        exists=db.scalar(select(GrowthEvent.id).where(GrowthEvent.company_id==p.company_id,GrowthEvent.event_name=='first_publication').limit(1))
        if not exists: db.add(GrowthEvent(company_id=p.company_id,user_id=p.user_id,event_name='first_publication',source='product'))
    elif status=='FAILED':pub.status='error';pub.error_message=data.get('fail_reason') or 'TikTok informou falha no processamento.'
    else:pub.status='processing'
    db.commit();return {**_publication_json(pub),'tiktok_status':data}

@router.get('/connections')
def connections(p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    found={x.platform:x for x in db.scalars(select(SocialConnection).where(SocialConnection.company_id==p.company_id)).all()}
    config={'TikTok':bool(settings.tiktok_client_key and settings.tiktok_client_secret and settings.tiktok_redirect_uri),'Instagram':bool(settings.meta_app_id and settings.meta_app_secret and settings.meta_redirect_uri),'YouTube Shorts':bool(settings.youtube_client_id and settings.youtube_client_secret and settings.youtube_redirect_uri),'Pinterest':bool(settings.pinterest_client_id and settings.pinterest_client_secret and settings.pinterest_redirect_uri)}
    access={'Pinterest':settings.pinterest_access_status}
    return [{'platform':p,'configured':config[p],'connected':p in found,'account_name':found[p].account_name if p in found else '','expires_at':found[p].expires_at.isoformat() if p in found and found[p].expires_at else None,'access_status':access.get(p,'ready')} for p in PLATFORMS]

@router.post('/tiktok/authorize')
def tiktok_authorize(p:Principal=Depends(require_role('ADMIN')),db:Session=Depends(get_db)):
    if not(settings.tiktok_client_key and settings.tiktok_client_secret and settings.tiktok_redirect_uri):raise HTTPException(409,'Configure TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET e TIKTOK_REDIRECT_URI')
    state=secrets.token_urlsafe(32);db.add(SocialOAuthAttempt(company_id=p.company_id,platform='TikTok',state=state));db.commit()
    params={'client_key':settings.tiktok_client_key,'response_type':'code','scope':'user.info.basic,video.publish','redirect_uri':settings.tiktok_redirect_uri,'state':state}
    return {'authorization_url':'https://www.tiktok.com/v2/auth/authorize/?'+urlencode(params)}

@router.get('/tiktok/callback')
async def tiktok_callback(code:str=Query(''),state:str=Query(''),error:str=Query(''),db:Session=Depends(get_db)):
    if error:return RedirectResponse(settings.frontend_url+'/integracoes?social_error='+error)
    attempt=db.scalar(select(SocialOAuthAttempt).where(SocialOAuthAttempt.platform=='TikTok',SocialOAuthAttempt.state==state))
    if not attempt or not code:raise HTTPException(400,'Callback TikTok inválido ou state expirado')
    if datetime.utcnow()-attempt.created_at>timedelta(minutes=15):raise HTTPException(400,'State expirado')
    form={'client_key':settings.tiktok_client_key,'client_secret':settings.tiktok_client_secret,'code':code,'grant_type':'authorization_code','redirect_uri':settings.tiktok_redirect_uri}
    async with httpx.AsyncClient(timeout=30) as client:r=await client.post('https://open.tiktokapis.com/v2/oauth/token/',data=form,headers={'Content-Type':'application/x-www-form-urlencoded'})
    data=r.json()
    if r.status_code>=400 or not data.get('access_token'):raise HTTPException(502,f'Falha ao conectar TikTok: {data}')
    conn=db.scalar(select(SocialConnection).where(SocialConnection.company_id==attempt.company_id,SocialConnection.platform=='TikTok')) or SocialConnection(company_id=attempt.company_id,platform='TikTok')
    conn.external_user_id=data.get('open_id','');conn.account_name='TikTok';conn.access_token_enc=encrypt(data['access_token']);conn.refresh_token_enc=encrypt(data.get('refresh_token',''));conn.scopes=data.get('scope','');conn.expires_at=datetime.utcnow()+timedelta(seconds=int(data.get('expires_in',86400)));conn.connected_at=datetime.utcnow()
    db.add(conn);db.delete(attempt);db.commit();return RedirectResponse(settings.frontend_url+'/integracoes?social_connected=tiktok',status_code=303)

@router.post('/pinterest/authorize')
def pinterest_authorize(p:Principal=Depends(require_role('ADMIN')),db:Session=Depends(get_db)):
    if not(settings.pinterest_client_id and settings.pinterest_client_secret and settings.pinterest_redirect_uri):
        raise HTTPException(409,'Configure PINTEREST_CLIENT_ID, PINTEREST_CLIENT_SECRET e PINTEREST_REDIRECT_URI')
    state=secrets.token_urlsafe(32);db.add(SocialOAuthAttempt(company_id=p.company_id,platform='Pinterest',state=state));db.commit()
    params={'client_id':settings.pinterest_client_id,'redirect_uri':settings.pinterest_redirect_uri,'response_type':'code','scope':'boards:read,boards:write,pins:read,pins:write,user_accounts:read','state':state}
    return {'authorization_url':'https://www.pinterest.com/oauth/?'+urlencode(params)}

@router.get('/pinterest/callback')
async def pinterest_callback(code:str=Query(''),state:str=Query(''),error:str=Query(''),db:Session=Depends(get_db)):
    if error:return RedirectResponse(settings.frontend_url+'/integracoes?social_error='+error,status_code=303)
    attempt=db.scalar(select(SocialOAuthAttempt).where(SocialOAuthAttempt.platform=='Pinterest',SocialOAuthAttempt.state==state))
    if not attempt or not code:raise HTTPException(400,'Callback Pinterest inválido ou state expirado')
    if datetime.utcnow()-attempt.created_at>timedelta(minutes=15):raise HTTPException(400,'State Pinterest expirado')
    import base64
    basic=base64.b64encode(f'{settings.pinterest_client_id}:{settings.pinterest_client_secret}'.encode()).decode()
    form={'grant_type':'authorization_code','code':code,'redirect_uri':settings.pinterest_redirect_uri}
    async with httpx.AsyncClient(timeout=30) as client:
        r=await client.post('https://api.pinterest.com/v5/oauth/token',data=form,headers={'Authorization':f'Basic {basic}','Content-Type':'application/x-www-form-urlencoded'})
    try:data=r.json()
    except Exception:raise HTTPException(502,f'Pinterest OAuth retornou HTTP {r.status_code}')
    if r.status_code>=400 or not data.get('access_token'):raise HTTPException(502,f'Falha ao conectar Pinterest: {data}')
    conn=db.scalar(select(SocialConnection).where(SocialConnection.company_id==attempt.company_id,SocialConnection.platform=='Pinterest')) or SocialConnection(company_id=attempt.company_id,platform='Pinterest')
    conn.account_name='Pinterest';conn.access_token_enc=encrypt(data['access_token']);conn.refresh_token_enc=encrypt(data.get('refresh_token',''));conn.scopes=data.get('scope','boards:read,boards:write,pins:read,pins:write,user_accounts:read');conn.expires_at=datetime.utcnow()+timedelta(seconds=int(data.get('expires_in',2592000)));conn.connected_at=datetime.utcnow()
    db.add(conn);db.delete(attempt);db.commit();return RedirectResponse(settings.frontend_url+'/integracoes?social_connected=pinterest',status_code=303)

@router.get('/pinterest/boards')
async def list_pinterest_boards(p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    conn=db.scalar(select(SocialConnection).where(SocialConnection.company_id==p.company_id,SocialConnection.platform=='Pinterest'))
    if not conn:raise HTTPException(409,'Conecte o Pinterest em Integrações.')
    try:items=await pinterest_boards(conn)
    except PublishError as e:raise HTTPException(502,str(e))
    return [{'id':str(x.get('id') or ''),'name':x.get('name') or '', 'privacy':x.get('privacy') or ''} for x in items]

@router.delete('/connections/{platform}')
def disconnect(platform:str,p:Principal=Depends(require_role('ADMIN')),db:Session=Depends(get_db)):
    conn=db.scalar(select(SocialConnection).where(SocialConnection.company_id==p.company_id,SocialConnection.platform==platform))
    if conn:db.delete(conn);db.commit()
    return {'connected':False,'platform':platform}
