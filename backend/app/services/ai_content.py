from __future__ import annotations
import json,re,httpx
from fastapi import HTTPException
from app.core.config import settings
BASE='https://api.openai.com/v1'
def headers():
    if not settings.openai_api_key: raise HTTPException(503,'IA não configurada. Configure OPENAI_API_KEY no Railway.')
    return {'Authorization':f'Bearer {settings.openai_api_key}'}
def output_text(data):
    if isinstance(data.get('output_text'),str): return data['output_text']
    out=[]
    for item in data.get('output',[]):
        if isinstance(item,dict):
            for c in item.get('content',[]):
                if isinstance(c,dict) and isinstance(c.get('text'),str):out.append(c['text'])
    return '\n'.join(out)
def parse_json(text):
    text=re.sub(r'^```(?:json)?\s*|\s*```$','',text.strip(),flags=re.I|re.S)
    try:return json.loads(text)
    except Exception:
        a,b=text.find('{'),text.rfind('}')
        if a>=0 and b>a:return json.loads(text[a:b+1])
        raise HTTPException(502,'A IA retornou formato inesperado.')
async def generate_copy(product,platform,duration,tone,audience):
    facts={'title':product.title,'marketplace':product.marketplace,'price':product.price,'original_price':product.original_price,'commission_rate':product.commission_rate,'affiliate_url':product.affiliate_url,'category':product.category}
    prompt=f'''Crie conteúdo de afiliado em português do Brasil. Use SOMENTE os fatos JSON; não invente desconto, avaliação, benefício, estoque, venda ou característica ausente. Canal={platform}; duração={duration}s; tom={tone}; público={audience or 'geral'}. FATOS={json.dumps(facts,ensure_ascii=False)}. Retorne APENAS JSON válido: title, hook, script, caption, hashtags, cta, video_prompt. Script com marcações de tempo. Inclua disclosure publicitário apropriado. video_prompt: vídeo vertical 9:16, comercial, sem texto/logos/claims inventados.'''
    async with httpx.AsyncClient(timeout=90) as c:r=await c.post(BASE+'/responses',headers={**headers(),'Content-Type':'application/json'},json={'model':settings.openai_text_model,'input':prompt})
    if r.status_code>=400:raise HTTPException(502,f'Falha na IA de texto ({r.status_code}): {r.text[:250]}')
    return parse_json(output_text(r.json()))
async def start_video(prompt,seconds=8):
    seconds=min((4,8,12),key=lambda x:abs(x-seconds))
    async with httpx.AsyncClient(timeout=60) as c:r=await c.post(BASE+'/videos',headers=headers(),data={'model':settings.openai_video_model,'prompt':prompt,'seconds':str(seconds),'size':'720x1280'})
    if r.status_code>=400:raise HTTPException(502,f'Falha ao iniciar vídeo IA ({r.status_code}): {r.text[:250]}')
    return r.json()
async def video_status(video_id):
    async with httpx.AsyncClient(timeout=45) as c:r=await c.get(BASE+f'/videos/{video_id}',headers=headers())
    if r.status_code>=400:raise HTTPException(502,f'Falha ao consultar vídeo IA ({r.status_code}).')
    return r.json()
async def download_video(video_id):
    async with httpx.AsyncClient(timeout=120) as c:r=await c.get(BASE+f'/videos/{video_id}/content',headers=headers())
    if r.status_code>=400:raise HTTPException(502,f'Falha ao baixar vídeo IA ({r.status_code}).')
    return r.content
