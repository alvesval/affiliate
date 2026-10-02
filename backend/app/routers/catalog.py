"""Controlled item-by-ID importer. Does not pretend public search or affiliate APIs are granted."""
import re
from datetime import datetime, timezone
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.entities import Product, ProductPrice
from app.models.oauth import MercadoLivreOAuth
from app.routers.mercadolivre import decrypt, refresh_company, configured
from app.core.auth import current_principal, require_role, Principal

router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])
ITEM_PATTERN = re.compile(r"^MLB\d{6,20}$", re.I)

class ImportRequest(BaseModel):
    item_ids: list[str] = Field(min_length=1, max_length=30)

class AffiliateUpdate(BaseModel):
    affiliate_url: str = Field(max_length=1000)
    commission_rate: float = Field(ge=0, le=100)
    affiliate_label: str = Field(default="", max_length=120)

async def access_token(db, company_id):
    configured()
    record=db.scalar(select(MercadoLivreOAuth).where(MercadoLivreOAuth.company_id==company_id))
    if not record or not record.access_token_encrypted:
        raise HTTPException(409,"Conecte sua conta Mercado Livre em Integrações")
    if record.expires_at and record.expires_at <= datetime.now(timezone.utc).replace(tzinfo=None):
        await refresh_company(db,company_id)
        db.refresh(record)
    return decrypt(record.access_token_encrypted)

@router.post("/mercadolivre/import")
async def import_items(payload:ImportRequest, p:Principal=Depends(require_role("EDITOR")), db:Session=Depends(get_db)):
    ids=list(dict.fromkeys(x.strip().upper() for x in payload.item_ids))
    invalid=[x for x in ids if not ITEM_PATTERN.fullmatch(x)]
    if invalid: raise HTTPException(422,f"IDs inválidos: {', '.join(invalid[:5])}")
    token=await access_token(db,p.company_id)
    results=[]
    async with httpx.AsyncClient(timeout=18, follow_redirects=False) as client:
        for item_id in ids:
            try:
                response = await client.get(
                    f"https://api.mercadolibre.com/items/{item_id}",
                    headers={"Authorization": f"Bearer {token}"}
                )

                if response.status_code != 200:
                    try:
                        erro = response.json()
                    except ValueError:
                        erro = {}

                    codigo = erro.get("code") or erro.get("error") or "sem_codigo"
                    mensagem = erro.get("message") or "Sem detalhes"

                    results.append({
                        "id": item_id,
                        "status": "error",
                        "reason": (
                            f"HTTP {response.status_code} | "
                            f"Código: {codigo} | "
                            f"Mensagem: {mensagem}"
                        )
                    })
                    continue
                data=response.json()
                if not data.get("id") or not data.get("title"):
                    results.append({"id":item_id,"status":"error","reason":"Resposta sem identificação ou título"});continue
                item=db.scalar(select(Product).where(Product.company_id==p.company_id,Product.marketplace=="Mercado Livre",Product.external_id==item_id))
                created=item is None
                if created:
                    item=Product(company_id=p.company_id,marketplace="Mercado Livre",external_id=item_id,title=str(data["title"])[:300])
                    db.add(item)
                price=float(data.get("price") or 0)
                if price <= 0: results.append({"id":item_id,"status":"error","reason":"Preço indisponível"});db.rollback();continue
                item.title=str(data["title"])[:300]
                item.price=price
                item.category=str(data.get("category_id") or "Não informada")[:100]
                item.image_url=str((data.get("pictures") or [{}])[0].get("secure_url") or data.get("secure_thumbnail") or data.get("thumbnail") or "")[:2000]
                item.permalink=str(data.get("permalink") or "")[:2000]
                item.source="mercadolivre_api"
                item.synced_at=datetime.now(timezone.utc).replace(tzinfo=None)
                db.flush()
                db.add(ProductPrice(company_id=p.company_id,product_id=item.id,price=price))
                db.commit()
                results.append({"id":item_id,"status":"created" if created else "updated","product_id":item.id})
            except (httpx.HTTPError,ValueError,TypeError) as exc:
                db.rollback()
                results.append({"id":item_id,"status":"error","reason":f"Falha ao consultar anúncio ({type(exc).__name__})"})
    return {"results":results,"created":sum(x["status"]=="created" for x in results),"updated":sum(x["status"]=="updated" for x in results),"errors":sum(x["status"]=="error" for x in results)}

@router.patch("/products/{product_id}/affiliate")
def affiliate(product_id:int, payload:AffiliateUpdate, p:Principal=Depends(require_role("EDITOR")), db:Session=Depends(get_db)):
    obj=db.scalar(select(Product).where(Product.id==product_id,Product.company_id==p.company_id))
    if not obj: raise HTTPException(404,"Produto não encontrado")
    if payload.affiliate_url and not payload.affiliate_url.startswith("https://"):
        raise HTTPException(422,"Informe link de afiliado HTTPS")
    obj.affiliate_url=payload.affiliate_url
    obj.commission_rate=payload.commission_rate
    obj.affiliate_label=payload.affiliate_label.strip()
    obj.affiliate_source="manual_mercadolivre_affiliates" if obj.affiliate_url else ""
    obj.affiliate_verified_at=datetime.now(timezone.utc).replace(tzinfo=None) if obj.affiliate_url else None
    db.commit()
    return {"id":obj.id,"affiliate_ready":bool(obj.affiliate_url and obj.commission_rate>0)}
