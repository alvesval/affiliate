"""Affiliate onboarding with a simple link-first flow plus an advanced batch importer."""
import hashlib
import re
from datetime import datetime, timezone
from urllib.parse import urlparse, unquote

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.entities import Product
from app.routers.mercadolivre import require_admin
from app.services.affiliate_provider import analyze_mercadolivre_url

router=APIRouter(prefix="/api/v1/affiliates", tags=["affiliates"])
ID_RE=re.compile(r"\bMLB[0-9]{6,20}\b", re.I)
ALLOWED_ORIGINAL={"mercadolivre.com.br","www.mercadolivre.com.br","produto.mercadolivre.com.br","lista.mercadolivre.com.br"}
ALLOWED_AFFILIATE={"meli.la","www.mercadolivre.com.br","mercadolivre.com.br","produto.mercadolivre.com.br"}

def validate_url(value:str, hosts:set[str], field:str)->str:
    value=value.strip(); parsed=urlparse(value)
    if parsed.scheme!="https" or parsed.hostname not in hosts or parsed.username or parsed.password or parsed.port:
        raise ValueError(f"{field}: use uma URL HTTPS de domínio oficial permitido")
    if len(value)>2000: raise ValueError(f"{field}: URL muito longa")
    return value

class AnalyzeRequest(BaseModel):
    url: str = Field(min_length=12, max_length=2000)

class QuickSaveRequest(BaseModel):
    analyzed_url: str = Field(min_length=12, max_length=2000)
    resolved_url: str | None = Field(default=None, max_length=2000)
    affiliate_url: str | None = Field(default=None, max_length=2000)
    title: str = Field(min_length=3, max_length=300)
    external_id: str | None = Field(default=None, max_length=30)
    image_url: str | None = Field(default=None, max_length=2000)
    price: float | None = Field(default=None, gt=0)
    commission_rate: float | None = Field(default=None, ge=0, le=100)
    label: str = Field(default="", max_length=120)

@router.post("/mercadolivre/analyze")
async def analyze(payload: AnalyzeRequest):
    try:
        return await analyze_mercadolivre_url(payload.url)
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    except Exception:
        raise HTTPException(502, "Não foi possível analisar o link agora. Tente novamente.")

@router.post("/mercadolivre/quick-save", dependencies=[Depends(require_admin)])
def quick_save(payload: QuickSaveRequest, db:Session=Depends(get_db)):
    try:
        analyzed=validate_url(payload.analyzed_url, ALLOWED_ORIGINAL|ALLOWED_AFFILIATE, "Link")
        resolved=validate_url(payload.resolved_url, ALLOWED_ORIGINAL|ALLOWED_AFFILIATE, "URL resolvida") if payload.resolved_url else analyzed
        affiliate=validate_url(payload.affiliate_url, ALLOWED_AFFILIATE, "Link de afiliado") if payload.affiliate_url else ""
    except ValueError as exc:
        raise HTTPException(422, str(exc))
    external=(payload.external_id or "").strip().upper() or None
    if external and not ID_RE.fullmatch(external): raise HTTPException(422,"ID MLB inválido")
    stmt=select(Product).where(Product.marketplace=="Mercado Livre")
    product=db.scalar(stmt.where(Product.external_id==external)) if external else None
    if product is None:
        product=db.scalar(stmt.where(Product.permalink==resolved))
    if product is None and affiliate:
        product=db.scalar(stmt.where(Product.affiliate_url==affiliate))
    created=product is None
    if created:
        key=external or "URL-"+hashlib.sha256(resolved.encode()).hexdigest()[:24].upper()
        product=Product(marketplace="Mercado Livre",external_id=key,title=payload.title.strip(),source="affiliate_assisted")
        db.add(product)
    product.title=payload.title.strip(); product.permalink=resolved
    if payload.image_url: product.image_url=payload.image_url
    if payload.price is not None: product.price=payload.price
    if affiliate:
        product.affiliate_url=affiliate; product.affiliate_label=payload.label.strip(); product.affiliate_source="assisted_official_link"
        product.affiliate_verified_at=datetime.now(timezone.utc).replace(tzinfo=None)
    if payload.commission_rate is not None: product.commission_rate=payload.commission_rate
    db.commit(); db.refresh(product)
    return {"status":"created" if created else "updated","product_id":product.id,"affiliate_ready":bool(product.affiliate_url and product.commission_rate>0)}

class AffiliateRow(BaseModel):
    original_url:str=Field(min_length=12,max_length=2000); affiliate_url:str=Field(min_length=12,max_length=2000); title:str=Field(min_length=3,max_length=300)
    price:float|None=Field(default=None,gt=0); commission_rate:float|None=Field(default=None,ge=0,le=100); label:str=Field(default="",max_length=120); external_id:str|None=Field(default=None,max_length=30)
    @model_validator(mode="after")
    def check(self):
        self.original_url=validate_url(self.original_url,ALLOWED_ORIGINAL,"URL original"); self.affiliate_url=validate_url(self.affiliate_url,ALLOWED_AFFILIATE,"Link de afiliado")
        parsed=urlparse(self.affiliate_url)
        if parsed.hostname!="meli.la" and not parsed.path.startswith(("/social/", "/MLB", "/p/")): raise ValueError("Link remunerado não reconhecido; utilize o link gerado pelo painel")
        match=ID_RE.search(unquote(self.original_url)); supplied=self.external_id.strip().upper() if self.external_id else None
        if supplied and not ID_RE.fullmatch(supplied): raise ValueError("ID de anúncio inválido")
        if supplied and match and supplied!=match.group(0).upper(): raise ValueError("ID não corresponde à URL original")
        self.external_id=supplied or (match.group(0).upper() if match else None); self.title=self.title.strip(); self.label=self.label.strip(); return self

class BatchRequest(BaseModel): items:list[AffiliateRow]=Field(min_length=1,max_length=100)

@router.post("/mercadolivre/batch",dependencies=[Depends(require_admin)])
def import_affiliates(payload:BatchRequest,db:Session=Depends(get_db)):
    results=[]
    for index,row in enumerate(payload.items,1):
        try:
            stmt=select(Product).where(Product.marketplace=="Mercado Livre"); product=db.scalar(stmt.where(Product.external_id==row.external_id)) if row.external_id else None
            if product is None: product=db.scalar(stmt.where(Product.permalink==row.original_url))
            if product is None: product=db.scalar(stmt.where(Product.affiliate_url==row.affiliate_url))
            created=product is None
            if created:
                key=row.external_id or "URL-"+hashlib.sha256(row.original_url.encode()).hexdigest()[:24].upper(); product=Product(marketplace="Mercado Livre",external_id=key,title=row.title,source="affiliate_manual"); db.add(product)
            product.title=row.title; product.permalink=row.original_url; product.affiliate_url=row.affiliate_url; product.affiliate_label=row.label; product.affiliate_source="manual_mercadolivre_affiliates"; product.affiliate_verified_at=datetime.now(timezone.utc).replace(tzinfo=None)
            if row.price is not None: product.price=row.price
            if row.commission_rate is not None: product.commission_rate=row.commission_rate
            db.commit(); results.append({"row":index,"status":"created" if created else "updated","product_id":product.id})
        except Exception:
            db.rollback(); results.append({"row":index,"status":"error","reason":"Não foi possível salvar este registro; verifique os dados e tente novamente"})
    return {"created":sum(r["status"]=="created" for r in results),"updated":sum(r["status"]=="updated" for r in results),"errors":sum(r["status"]=="error" for r in results),"results":results}
