from __future__ import annotations
import math
import httpx
from app.services.social_crypto import decrypt
from app.services.media_storage import get_bytes
from app.models.social import SocialConnection, ContentVariant, Publication

class PublishError(RuntimeError): pass

API='https://open.tiktokapis.com'

async def tiktok_creator_info(conn:SocialConnection)->dict:
    token=decrypt(conn.access_token_enc)
    headers={'Authorization':f'Bearer {token}','Content-Type':'application/json; charset=UTF-8'}
    async with httpx.AsyncClient(timeout=30) as client:
        r=await client.post(f'{API}/v2/post/publish/creator_info/query/',headers=headers,json={})
    try:data=r.json()
    except Exception:raise PublishError(f'TikTok creator info retornou HTTP {r.status_code}.')
    if r.status_code>=400 or (data.get('error') or {}).get('code') not in (None,'ok'):
        raise PublishError(f'TikTok recusou creator info: {data}')
    return data.get('data') or {}

def _chunk_plan(size:int)->tuple[int,int]:
    # TikTok: chunk intermediário entre 5 MiB e 64 MiB. Para arquivos <=64 MiB, um único chunk.
    if size<=0: raise PublishError('Arquivo de vídeo vazio.')
    max_chunk=64*1024*1024
    if size<=max_chunk:return size,1
    count=math.ceil(size/max_chunk)
    chunk=math.ceil(size/count)
    return chunk,count

async def _upload_tiktok(upload_url:str, data:bytes, content_type:str, chunk_size:int)->None:
    total=len(data)
    async with httpx.AsyncClient(timeout=180,follow_redirects=True) as client:
        start=0
        while start<total:
            end=min(start+chunk_size,total)-1
            body=data[start:end+1]
            headers={'Content-Type':content_type,'Content-Length':str(len(body)),'Content-Range':f'bytes {start}-{end}/{total}'}
            r=await client.put(upload_url,headers=headers,content=body)
            if r.status_code>=400:
                raise PublishError(f'Falha no upload do vídeo ao TikTok: HTTP {r.status_code} {r.text[:500]}')
            start=end+1

async def publish_tiktok(conn:SocialConnection, variant:ContentVariant, publication:Publication)->dict:
    if not variant.media_storage_key:
        raise PublishError('TikTok exige um vídeo enviado pelo Estúdio antes de publicar.')
    if not publication.user_consent:
        raise PublishError('Confirmação do usuário é obrigatória antes do envio ao TikTok.')
    creator=await tiktok_creator_info(conn)
    options=creator.get('privacy_level_options') or []
    if publication.privacy_level not in options:
        raise PublishError('A privacidade escolhida não está mais disponível. Reabra as opções de publicação do TikTok.')
    data=get_bytes(variant.media_storage_key)
    size=len(data)
    max_duration=int(creator.get('max_video_post_duration_sec') or 0)
    content_type=variant.media_content_type or 'video/mp4'
    if content_type not in ('video/mp4','video/quicktime','video/webm'):
        raise PublishError('Formato não suportado para Direct Post. Use MP4, MOV ou WebM.')
    chunk_size,total_chunks=_chunk_plan(size)
    token=decrypt(conn.access_token_enc)
    headers={'Authorization':f'Bearer {token}','Content-Type':'application/json; charset=UTF-8'}
    payload={
      'post_info':{
        'title':(variant.caption or variant.title)[:2200],
        'privacy_level':publication.privacy_level,
        'disable_duet':bool(publication.disable_duet or creator.get('duet_disabled')),
        'disable_comment':bool(publication.disable_comment or creator.get('comment_disabled')),
        'disable_stitch':bool(publication.disable_stitch or creator.get('stitch_disabled')),
        'brand_content_toggle':bool(publication.brand_content_toggle),
        'brand_organic_toggle':bool(publication.brand_organic_toggle),
        'is_aigc':bool(publication.is_aigc),
      },
      'source_info':{'source':'FILE_UPLOAD','video_size':size,'chunk_size':chunk_size,'total_chunk_count':total_chunks}
    }
    async with httpx.AsyncClient(timeout=30,follow_redirects=True) as client:
        r=await client.post(f'{API}/v2/post/publish/video/init/',headers=headers,json=payload)
    try:resp=r.json()
    except Exception:raise PublishError(f'TikTok init retornou HTTP {r.status_code}.')
    if r.status_code>=400 or (resp.get('error') or {}).get('code') not in (None,'ok'):
        raise PublishError(f'TikTok recusou a publicação: {resp}')
    out=resp.get('data') or {}
    publish_id=out.get('publish_id','');upload_url=out.get('upload_url','')
    if not publish_id or not upload_url:raise PublishError('TikTok não retornou publish_id/upload_url.')
    await _upload_tiktok(upload_url,data,content_type,chunk_size)
    return {'external_post_id':publish_id,'external_post_url':'','status':'processing','max_video_post_duration_sec':max_duration}

async def fetch_tiktok_status(conn:SocialConnection,publish_id:str)->dict:
    token=decrypt(conn.access_token_enc)
    headers={'Authorization':f'Bearer {token}','Content-Type':'application/json; charset=UTF-8'}
    async with httpx.AsyncClient(timeout=30) as client:
        r=await client.post(f'{API}/v2/post/publish/status/fetch/',headers=headers,json={'publish_id':publish_id})
    try:data=r.json()
    except Exception:raise PublishError(f'TikTok status retornou HTTP {r.status_code}.')
    if r.status_code>=400 or (data.get('error') or {}).get('code') not in (None,'ok'):
        raise PublishError(f'Falha ao consultar status TikTok: {data}')
    return data.get('data') or {}

async def publish(platform:str, conn:SocialConnection|None, variant:ContentVariant, publication:Publication)->dict:
    if not conn:raise PublishError(f'Conecte sua conta {platform} em Integrações antes de publicar.')
    if platform=='TikTok':return await publish_tiktok(conn,variant,publication)
    if platform=='Pinterest':return await publish_pinterest(conn,variant,publication)
    raise PublishError(f'{platform}: provider preparado, mas publicação real será habilitada após OAuth/permissões da plataforma.')

PINTEREST_PROD_API='https://api.pinterest.com/v5'
PINTEREST_SANDBOX_API='https://api-sandbox.pinterest.com/v5'

def pinterest_environment()->str:
    from app.core.config import settings
    return 'production' if (settings.pinterest_access_status or '').lower()=='standard' else 'sandbox'

def _pinterest_api()->str:
    return PINTEREST_PROD_API if pinterest_environment()=='production' else PINTEREST_SANDBOX_API
PINTEREST_PUBLISH_SCOPES={'boards:read','boards:write','pins:read','pins:write'}

def _pinterest_scopes(conn:SocialConnection)->set[str]:
    raw=(getattr(conn,'scopes','') or '').replace(',', ' ')
    return {x.strip() for x in raw.split() if x.strip()}

def _ensure_pinterest_publish_scopes(conn:SocialConnection)->None:
    missing=sorted(PINTEREST_PUBLISH_SCOPES-_pinterest_scopes(conn))
    if missing:
        raise PublishError(
            'A conexão do Pinterest não possui todas as permissões necessárias para publicar. '
            f'Permissões ausentes: {", ".join(missing)}. '
            'Vá em Integrações, desconecte/conecte novamente o Pinterest e autorize as novas permissões.'
        )

def _pinterest_api_error(prefix:str, data:dict)->PublishError:
    message=str((data or {}).get('message') or '')
    missing=[]
    if 'Missing:' in message:
        import re
        missing=re.findall(r"[a-z_]+:(?:read|write)(?:_secret)?", message)
    if missing:
        return PublishError(
            f'{prefix}: a autorização atual do Pinterest está incompleta. '
            f'Permissões ausentes: {", ".join(sorted(set(missing)))}. '
            'Reconecte o Pinterest em Integrações para atualizar as permissões.'
        )
    return PublishError(f'{prefix}: {data}')

async def pinterest_boards(conn:SocialConnection)->list[dict]:
    token=decrypt(conn.access_token_enc)
    headers={'Authorization':f'Bearer {token}','Accept':'application/json'}
    async with httpx.AsyncClient(timeout=30) as client:
        r=await client.get(f'{_pinterest_api()}/boards',headers=headers,params={'page_size':100})
    try:data=r.json()
    except Exception: raise PublishError(f'Pinterest boards retornou HTTP {r.status_code}.')
    if r.status_code>=400: raise PublishError(f'Pinterest recusou a consulta de boards: {data}')
    return data.get('items') or []

async def create_pinterest_board(conn:SocialConnection, name:str='AIAffiliate Sandbox')->dict:
    token=decrypt(conn.access_token_enc)
    headers={'Authorization':f'Bearer {token}','Content-Type':'application/json','Accept':'application/json'}
    async with httpx.AsyncClient(timeout=30) as client:
        r=await client.post(f'{_pinterest_api()}/boards',headers=headers,json={'name':name[:180],'privacy':'PUBLIC'})
    try:data=r.json()
    except Exception: raise PublishError(f'Pinterest Create Board retornou HTTP {r.status_code}.')
    if r.status_code>=400: raise _pinterest_api_error('Pinterest recusou a criação da pasta de teste',data)
    return data

async def publish_pinterest(conn:SocialConnection, variant:ContentVariant, publication:Publication)->dict:
    _ensure_pinterest_publish_scopes(conn)
    board_id=getattr(publication,'pinterest_board_id','') or ''
    cover_url=getattr(publication,'pinterest_cover_url','') or ''
    if not board_id: raise PublishError('Selecione um board do Pinterest antes de publicar.')
    if not cover_url: raise PublishError('Pinterest exige uma imagem real do produto.')
    token=decrypt(conn.access_token_enc)
    headers={'Authorization':f'Bearer {token}','Content-Type':'application/json','Accept':'application/json'}
    api=_pinterest_api()

    # Trial usa obrigatoriamente Sandbox. O Sandbox não aceita Video Pins; para validar
    # o fluxo ponta a ponta publicamos um Image Pin com a capa real do produto.
    if pinterest_environment()=='sandbox':
        payload={'title':(variant.title or '')[:100],'description':(variant.caption or '')[:500],
                 'board_id':board_id,'link':variant.affiliate_url or '',
                 'media_source':{'source_type':'image_url','url':cover_url}}
        async with httpx.AsyncClient(timeout=60,follow_redirects=True) as client:
            pin=await client.post(f'{api}/pins',headers=headers,json=payload)
        try:pin_data=pin.json()
        except Exception: raise PublishError(f'Pinterest Sandbox Create Pin retornou HTTP {pin.status_code}.')
        if pin.status_code>=400: raise _pinterest_api_error('Pinterest Sandbox recusou o Image Pin de teste',pin_data)
        pin_id=str(pin_data.get('id') or '')
        return {'external_post_id':pin_id,'external_post_url':f'https://www.pinterest.com/pin/{pin_id}/' if pin_id else '',
                'status':'published','pinterest_environment':'sandbox','pinterest_format':'image'}

    # Standard: fluxo real de Video Pin em produção.
    if not variant.media_storage_key: raise PublishError('Pinterest exige um vídeo antes de publicar em produção.')
    video=get_bytes(variant.media_storage_key)
    async with httpx.AsyncClient(timeout=180,follow_redirects=True) as client:
        reg=await client.post(f'{api}/media',headers=headers,json={'media_type':'video'})
        try:reg_data=reg.json()
        except Exception: raise PublishError(f'Pinterest registro de mídia retornou HTTP {reg.status_code}.')
        if reg.status_code>=400: raise _pinterest_api_error('Pinterest recusou o registro do vídeo',reg_data)
        media_id=reg_data.get('media_id'); upload_url=reg_data.get('upload_url'); params=reg_data.get('upload_parameters') or {}
        if not media_id or not upload_url: raise PublishError('Pinterest não retornou media_id/upload_url.')
        files={'file':(variant.media_filename or 'video.mp4',video,variant.media_content_type or 'video/mp4')}
        up=await client.post(upload_url,data={str(k):str(v) for k,v in params.items()},files=files,headers={'Accept':'*/*'})
        if up.status_code not in (200,201,204): raise PublishError(f'Falha no upload do vídeo ao Pinterest: HTTP {up.status_code} {up.text[:500]}')
        import asyncio
        media_status={}
        for _ in range(30):
            chk=await client.get(f'{api}/media/{media_id}',headers={'Authorization':f'Bearer {token}','Accept':'application/json'})
            try:media_status=chk.json()
            except Exception: media_status={}
            status=str(media_status.get('status') or '').lower()
            if status=='succeeded': break
            if status in ('failed','error'): raise PublishError(f'Pinterest falhou ao processar o vídeo: {media_status}')
            await asyncio.sleep(2)
        else: raise PublishError('Pinterest ainda está processando o vídeo. Tente executar novamente em alguns instantes.')
        payload={'title':(variant.title or '')[:100],'description':(variant.caption or '')[:500],
                 'board_id':board_id,'link':variant.affiliate_url or '',
                 'media_source':{'source_type':'video_id','cover_image_url':cover_url,'media_id':media_id}}
        pin=await client.post(f'{api}/pins',headers=headers,json=payload)
        try:pin_data=pin.json()
        except Exception: raise PublishError(f'Pinterest Create Pin retornou HTTP {pin.status_code}.')
        if pin.status_code>=400: raise _pinterest_api_error('Pinterest recusou o Video Pin',pin_data)
    pin_id=str(pin_data.get('id') or '')
    return {'external_post_id':pin_id,'external_post_url':f'https://www.pinterest.com/pin/{pin_id}/' if pin_id else '',
            'status':'published','pinterest_environment':'production','pinterest_format':'video'}

