"""Deterministic editable drafts, not fabricated AI output or auto-publishing."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.entities import Product, ProductContent
from app.routers.mercadolivre import require_admin
router=APIRouter(prefix="/api/v1/content",tags=["content"])
class GenerateRequest(BaseModel):
    product_id:int
    channel:str="Instagram"

@router.get("",dependencies=[Depends(require_admin)])
def list_content(db:Session=Depends(get_db)):
    rows=db.scalars(select(ProductContent).order_by(ProductContent.id.desc()).limit(100)).all()
    return [{"id":r.id,"product_id":r.product_id,"channel":r.channel,"title":r.title,"hook":r.hook,"caption":r.caption,"script":r.script,"status":r.status,"created_at":r.created_at.isoformat()} for r in rows]

@router.post("/generate",dependencies=[Depends(require_admin)])
def generate(data:GenerateRequest,db:Session=Depends(get_db)):
    p=db.get(Product,data.product_id)
    if not p: raise HTTPException(404,"Produto não encontrado")
    if not p.affiliate_url: raise HTTPException(409,"Cadastre um link de afiliado válido antes de gerar conteúdo")
    channel=data.channel.strip()
    if channel not in {"Instagram","TikTok","YouTube Shorts","Pinterest","Site"}:raise HTTPException(422,"Canal inválido")
    hook=f"Conheça este produto: {p.title[:90]}"
    caption=f"{p.title}\nConfira os detalhes, preço e disponibilidade no link: {p.affiliate_url}\n\nPublicidade • Link de afiliado: posso receber comissão por compras qualificadas. Preços e condições sujeitos a alteração."
    script=f"Abertura: {hook}.\nMostre a imagem autorizada do anúncio.\nExplique características verificadas na página oficial, sem prometer resultados não comprovados.\nConvite: confira as condições atualizadas no link da descrição.\nInclua a identificação de publicidade e revise antes de publicar."
    item=ProductContent(product_id=p.id,channel=channel,title=p.title[:300],hook=hook,caption=caption,script=script,status="draft")
    db.add(item);db.commit();db.refresh(item)
    return {"id":item.id,"status":item.status,"channel":channel,"title":item.title,"hook":item.hook,"caption":item.caption,"script":item.script}
