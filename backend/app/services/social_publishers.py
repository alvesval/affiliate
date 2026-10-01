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
    raise PublishError(f'{platform}: provider preparado, mas publicação real será habilitada após OAuth/permissões da plataforma.')
