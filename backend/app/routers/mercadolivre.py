"""Mercado Livre OAuth + PKCE, isolated per SaaS company."""
import base64, hashlib, secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.db import get_db
from app.core.auth import current_principal, require_role, Principal
from app.models.oauth import MercadoLivreOAuth, OAuthAttempt

router=APIRouter(prefix='/api/integrations/mercadolivre',tags=['Mercado Livre OAuth'])
AUTHORIZE_URL='https://auth.mercadolivre.com.br/authorization'; TOKEN_URL='https://api.mercadolibre.com/oauth/token'

def configured():
    required = {
        "MELI_CLIENT_ID": settings.meli_client_id,
        "MELI_CLIENT_SECRET": settings.meli_client_secret,
        "MELI_REDIRECT_URI": settings.meli_redirect_uri,
        "TOKEN_ENCRYPTION_KEY": settings.token_encryption_key,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise HTTPException(503, detail={
            "code": "MELI_CONFIGURATION_INCOMPLETE",
            "message": "Integração Mercado Livre ainda não está configurada no servidor.",
            "missing": missing,
        })
    if not settings.meli_redirect_uri.startswith('https://'):
        raise HTTPException(503, detail={"code":"MELI_REDIRECT_URI_INVALID","message":"MELI_REDIRECT_URI deve usar HTTPS."})
def cipher():
    try:return Fernet(settings.token_encryption_key.encode())
    except (ValueError,TypeError) as e:raise HTTPException(503,'TOKEN_ENCRYPTION_KEY inválida') from e
def encrypt(v):return cipher().encrypt(v.encode()).decode()
def decrypt(v):
    try:return cipher().decrypt(v.encode()).decode()
    except InvalidToken as e:raise HTTPException(503,'Não foi possível descriptografar o token') from e
def challenge(v):return base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).rstrip(b'=').decode()
def _record(db,cid):return db.scalar(select(MercadoLivreOAuth).where(MercadoLivreOAuth.company_id==cid))

@router.post('/authorize')
def authorize(p:Principal=Depends(require_role('ADMIN')),db:Session=Depends(get_db)):
    configured();now=datetime.now(timezone.utc).replace(tzinfo=None);state=secrets.token_urlsafe(32);verifier=secrets.token_urlsafe(64)
    db.query(OAuthAttempt).filter(OAuthAttempt.expires_at<now).delete()
    db.add(OAuthAttempt(company_id=p.company_id,state_hash=hashlib.sha256(state.encode()).hexdigest(),verifier_encrypted=encrypt(verifier),expires_at=now+timedelta(minutes=10)));db.commit()
    params={'response_type':'code','client_id':settings.meli_client_id,'redirect_uri':settings.meli_redirect_uri,'state':state,'code_challenge':challenge(verifier),'code_challenge_method':'S256'}
    return {'authorization_url':AUTHORIZE_URL+'?'+urlencode(params)}

@router.get('/callback')
async def callback(code:str|None=None,state:str|None=None,error:str|None=None,db:Session=Depends(get_db)):
    if not state:raise HTTPException(400,'State ausente')
    attempt=db.scalar(select(OAuthAttempt).where(OAuthAttempt.state_hash==hashlib.sha256(state.encode()).hexdigest()));now=datetime.now(timezone.utc).replace(tzinfo=None)
    if not attempt or attempt.expires_at<now:raise HTTPException(400,'State inválido, expirado ou já utilizado')
    cid=attempt.company_id;verifier=decrypt(attempt.verifier_encrypted);db.delete(attempt);db.commit()
    if error or not code:return RedirectResponse(settings.frontend_url+'/integracoes?meli=cancelado',303)
    configured();payload={'grant_type':'authorization_code','client_id':settings.meli_client_id,'client_secret':settings.meli_client_secret,'code':code,'redirect_uri':settings.meli_redirect_uri,'code_verifier':verifier}
    try:
        async with httpx.AsyncClient(timeout=20) as client:r=await client.post(TOKEN_URL,data=payload);r.raise_for_status();data=r.json()
    except (httpx.HTTPError,ValueError) as e:raise HTTPException(502,'Falha na troca do código por token') from e
    if not data.get('access_token'):raise HTTPException(502,'Mercado Livre não retornou access_token')
    rec=_record(db,cid) or MercadoLivreOAuth(company_id=cid);rec.access_token_encrypted=encrypt(data['access_token']);rec.refresh_token_encrypted=encrypt(data.get('refresh_token','')) if data.get('refresh_token') else rec.refresh_token_encrypted;rec.expires_at=now+timedelta(seconds=max(0,int(data.get('expires_in',0))-60));rec.meli_user_id=str(data.get('user_id') or '');db.add(rec);db.commit()
    return RedirectResponse(settings.frontend_url+'/integracoes?meli=conectado',303)

@router.get('/status')
def status(p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    rec=_record(db,p.company_id);return {'connected':bool(rec and rec.access_token_encrypted),'user_id':rec.meli_user_id if rec else None,'expires_at':rec.expires_at.isoformat() if rec and rec.expires_at else None,'configured':all((settings.meli_client_id,settings.meli_client_secret,settings.meli_redirect_uri,settings.token_encryption_key))}

async def refresh_company(db:Session,company_id:int):
    configured();rec=_record(db,company_id)
    if not rec or not rec.refresh_token_encrypted:raise HTTPException(409,'Refresh token não disponível. Reconecte a conta')
    data={'grant_type':'refresh_token','client_id':settings.meli_client_id,'client_secret':settings.meli_client_secret,'refresh_token':decrypt(rec.refresh_token_encrypted)}
    try:
        async with httpx.AsyncClient(timeout=20) as client:r=await client.post(TOKEN_URL,data=data);r.raise_for_status();result=r.json()
    except (httpx.HTTPError,ValueError) as e:raise HTTPException(502,'Não foi possível renovar a autorização') from e
    if not result.get('access_token'):raise HTTPException(502,'Resposta sem access_token')
    rec.access_token_encrypted=encrypt(result['access_token']);rec.refresh_token_encrypted=encrypt(result.get('refresh_token','')) if result.get('refresh_token') else rec.refresh_token_encrypted;rec.expires_at=datetime.now(timezone.utc).replace(tzinfo=None)+timedelta(seconds=max(0,int(result.get('expires_in',0))-60));db.commit();return rec

@router.post('/refresh')
async def refresh(p:Principal=Depends(require_role('ADMIN')),db:Session=Depends(get_db)):
    rec=await refresh_company(db,p.company_id);return {'refreshed':True,'expires_at':rec.expires_at.isoformat()}

@router.post('/disconnect')
def disconnect(p:Principal=Depends(require_role('ADMIN')),db:Session=Depends(get_db)):
    rec=_record(db,p.company_id)
    if rec:db.delete(rec);db.commit()
    return {'connected':False,'note':'Credenciais desta empresa excluídas'}
