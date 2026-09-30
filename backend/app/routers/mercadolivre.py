"""Mercado Livre OAuth authorization-code + PKCE integration.

The V1 has no user login: administrative operations require a separately configured
ADMIN_SETUP_KEY. Do not expose this key to the Next.js bundle or public links.
"""
import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_db
from app.models.oauth import MercadoLivreOAuth, OAuthAttempt

router = APIRouter(prefix="/api/integrations/mercadolivre", tags=["Mercado Livre OAuth"])
AUTHORIZE_URL = "https://auth.mercadolivre.com.br/authorization"
TOKEN_URL = "https://api.mercadolibre.com/oauth/token"


def require_admin(x_admin_key: str | None = Header(default=None)):
    if not settings.admin_setup_key or not hmac.compare_digest(x_admin_key or "", settings.admin_setup_key):
        raise HTTPException(403, "Chave administrativa ausente ou inválida")


def configured():
    if not all((settings.meli_client_id, settings.meli_client_secret, settings.meli_redirect_uri, settings.token_encryption_key)):
        raise HTTPException(503, "Configure MELI_CLIENT_ID, MELI_CLIENT_SECRET, MELI_REDIRECT_URI e TOKEN_ENCRYPTION_KEY no .env")
    if not settings.meli_redirect_uri.startswith("https://"):
        raise HTTPException(503, "MELI_REDIRECT_URI deve usar HTTPS")


def cipher():
    try:
        return Fernet(settings.token_encryption_key.encode())
    except (ValueError, TypeError) as exc:
        raise HTTPException(503, "TOKEN_ENCRYPTION_KEY inválida: use uma chave Fernet") from exc


def encrypt(value: str) -> str:
    return cipher().encrypt(value.encode()).decode()


def decrypt(value: str) -> str:
    try:
        return cipher().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise HTTPException(503, "Não foi possível descriptografar o token. Verifique TOKEN_ENCRYPTION_KEY") from exc


def challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()


@router.post("/authorize", dependencies=[Depends(require_admin)])
def authorize(db: Session = Depends(get_db)):
    configured()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    # One-use, short-lived state; the verifier never leaves the backend.
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    db.query(OAuthAttempt).filter(OAuthAttempt.expires_at < now).delete()
    db.add(OAuthAttempt(state_hash=hashlib.sha256(state.encode()).hexdigest(), verifier_encrypted=encrypt(verifier), expires_at=now + timedelta(minutes=10)))
    db.commit()
    params = {"response_type": "code", "client_id": settings.meli_client_id,
              "redirect_uri": settings.meli_redirect_uri, "state": state,
              "code_challenge": challenge(verifier), "code_challenge_method": "S256"}
    return {"authorization_url": f"{AUTHORIZE_URL}?{urlencode(params)}"}


@router.get("/callback")
async def callback(code: str | None = None, state: str | None = None, error: str | None = None,
                   db: Session = Depends(get_db)):
    # The OAuth provider redirects a browser here. Never reflect tokens or provider errors.
    if not state:
        raise HTTPException(400, "State ausente")
    state_hash = hashlib.sha256(state.encode()).hexdigest()
    attempt = db.query(OAuthAttempt).filter_by(state_hash=state_hash).first()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if not attempt or attempt.expires_at < now:
        raise HTTPException(400, "State inválido, expirado ou já utilizado")
    verifier = decrypt(attempt.verifier_encrypted)
    db.delete(attempt)
    db.commit()  # consume state even if exchange fails
    if error or not code:
        return RedirectResponse("http://localhost:3000/integracoes?meli=cancelado", status_code=303)
    configured()
    payload = {"grant_type": "authorization_code", "client_id": settings.meli_client_id,
               "client_secret": settings.meli_client_secret, "code": code,
               "redirect_uri": settings.meli_redirect_uri, "code_verifier": verifier}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(TOKEN_URL, data=payload)
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, "Falha na troca do código por token. Verifique o log do backend e a configuração OAuth") from exc
    if not data.get("access_token"):
        raise HTTPException(502, "Mercado Livre não retornou access_token")
    record = db.query(MercadoLivreOAuth).filter_by(id=1).first()
    if record is None:
        record = MercadoLivreOAuth(id=1)
        db.add(record)
    record.access_token_encrypted = encrypt(data["access_token"])
    if data.get("refresh_token"):
        record.refresh_token_encrypted = encrypt(data["refresh_token"])
    record.expires_at = now + timedelta(seconds=max(0, int(data.get("expires_in", 0)) - 60))
    record.meli_user_id = str(data.get("user_id") or "")
    db.commit()
    return RedirectResponse("http://localhost:3000/integracoes?meli=conectado", status_code=303)


@router.get("/status", dependencies=[Depends(require_admin)])
def status(db: Session = Depends(get_db)):
    record = db.query(MercadoLivreOAuth).filter_by(id=1).first()
    return {"connected": bool(record and record.access_token_encrypted),
            "user_id": record.meli_user_id if record else None,
            "expires_at": record.expires_at.isoformat() if record and record.expires_at else None,
            "configured": all((settings.meli_client_id, settings.meli_client_secret, settings.meli_redirect_uri, settings.token_encryption_key))}


@router.post("/refresh", dependencies=[Depends(require_admin)])
async def refresh(db: Session = Depends(get_db)):
    configured()
    record = db.query(MercadoLivreOAuth).filter_by(id=1).first()
    if not record or not record.refresh_token_encrypted:
        raise HTTPException(409, "Refresh token não disponível. Reconecte a conta")
    data = {"grant_type": "refresh_token", "client_id": settings.meli_client_id,
            "client_secret": settings.meli_client_secret,
            "refresh_token": decrypt(record.refresh_token_encrypted)}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(TOKEN_URL, data=data)
            response.raise_for_status()
            result = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, "Não foi possível renovar a autorização") from exc
    if not result.get("access_token"):
        raise HTTPException(502, "Resposta sem access_token")
    record.access_token_encrypted = encrypt(result["access_token"])
    if result.get("refresh_token"):
        record.refresh_token_encrypted = encrypt(result["refresh_token"])
    record.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=max(0, int(result.get("expires_in", 0)) - 60))
    db.commit()
    return {"refreshed": True, "expires_at": record.expires_at.isoformat()}


@router.post("/disconnect", dependencies=[Depends(require_admin)])
def disconnect(db: Session = Depends(get_db)):
    db.query(MercadoLivreOAuth).delete()
    db.commit()
    return {"connected": False, "note": "Credenciais locais excluídas; revogue a autorização no Mercado Livre se necessário"}
