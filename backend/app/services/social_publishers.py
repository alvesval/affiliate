import httpx
from app.services.social_crypto import decrypt
from app.models.social import SocialConnection, ContentVariant

class PublishError(RuntimeError): pass

async def publish_tiktok(conn:SocialConnection, variant:ContentVariant)->dict:
    if not variant.media_url:
        raise PublishError('TikTok exige uma mídia. Informe uma URL HTTPS pública do vídeo antes de publicar.')
    token=decrypt(conn.access_token_enc)
    headers={'Authorization':f'Bearer {token}','Content-Type':'application/json; charset=UTF-8'}
    # PULL_FROM_URL exige que a URL/domínio atenda aos requisitos do TikTok.
    payload={'post_info':{'title':(variant.caption or variant.title)[:2200],'privacy_level':'SELF_ONLY','disable_duet':False,'disable_comment':False,'disable_stitch':False},'source_info':{'source':'PULL_FROM_URL','video_url':variant.media_url}}
    async with httpx.AsyncClient(timeout=30,follow_redirects=True) as client:
        r=await client.post('https://open.tiktokapis.com/v2/post/publish/video/init/',headers=headers,json=payload)
    data=r.json()
    if r.status_code>=400 or data.get('error',{}).get('code') not in (None,'ok'):
        raise PublishError(f'TikTok recusou a publicação: {data}')
    publish_id=(data.get('data') or {}).get('publish_id','')
    return {'external_post_id':publish_id,'external_post_url':''}

async def publish(platform:str, conn:SocialConnection|None, variant:ContentVariant)->dict:
    if not conn:
        raise PublishError(f'Conecte sua conta {platform} em Integrações antes de publicar.')
    if platform=='TikTok': return await publish_tiktok(conn,variant)
    raise PublishError(f'{platform}: provider preparado, mas publicação real será habilitada após OAuth/permissões da plataforma.')
