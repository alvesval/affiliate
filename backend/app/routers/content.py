"""Deterministic editable drafts, not fabricated AI output or auto-publishing."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.entities import Product, ProductContent
from app.core.auth import current_principal, require_role, Principal
router=APIRouter(prefix="/api/v1/content",tags=["content"])
class GenerateRequest(BaseModel):
    product_id:int
    channel:str="Instagram"

@router.get("")
def list_content(p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    rows=db.scalars(select(ProductContent).where(ProductContent.company_id==p.company_id).order_by(ProductContent.id.desc()).limit(100)).all()
    return [{"id":r.id,"product_id":r.product_id,"channel":r.channel,"title":r.title,"hook":r.hook,"caption":r.caption,"script":r.script,"status":r.status,"created_at":r.created_at.isoformat()} for r in rows]

@router.post("/generate")
def generate(data:GenerateRequest,p:Principal=Depends(require_role("EDITOR")),db:Session=Depends(get_db)):
    product=db.scalar(select(Product).where(Product.id==data.product_id,Product.company_id==p.company_id))
    if not product: raise HTTPException(404,"Produto não encontrado")
    if not product.affiliate_url: raise HTTPException(409,"Cadastre um link de afiliado válido antes de gerar conteúdo")
    channel=data.channel.strip()
    if channel not in {"Instagram","TikTok","YouTube Shorts","Pinterest","Site"}:raise HTTPException(422,"Canal inválido")
    hook=f"Conheça este produto: {product.title[:90]}"
    caption=f"{product.title}\nConfira os detalhes, preço e disponibilidade no link: {product.affiliate_url}\n\nPublicidade • Link de afiliado: posso receber comissão por compras qualificadas. Preços e condições sujeitos a alteração."
    script=f"Abertura: {hook}.\nMostre a imagem autorizada do anúncio.\nExplique características verificadas na página oficial, sem prometer resultados não comprovados.\nConvite: confira as condições atualizadas no link da descrição.\nInclua a identificação de publicidade e revise antes de publicar."
    item=ProductContent(company_id=p.company_id,product_id=product.id,channel=channel,title=product.title[:300],hook=hook,caption=caption,script=script,status="draft")
    db.add(item);db.commit();db.refresh(item)
    return {"id":item.id,"status":item.status,"channel":channel,"title":item.title,"hook":item.hook,"caption":item.caption,"script":item.script}
