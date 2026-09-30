from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.core.db import get_db
from app.models.entities import Product, ProductPrice
from app.schemas.product import ProductIn
from app.services.scoring import calculate_score
from app.routers.mercadolivre import require_admin

router = APIRouter(prefix="/products", tags=["products"])

def serialize(p, db):
    history = db.scalars(select(ProductPrice).where(ProductPrice.product_id == p.id).order_by(ProductPrice.captured_at.desc(), ProductPrice.id.desc()).limit(30)).all()
    prices = [x.price for x in history]
    # A single advertised crossed-out price is not a verified historical discount.
    historical = prices[1:]
    baseline = min(historical) if len(historical) >= 2 else None
    verified_discount = round((baseline-p.price)/baseline*100,2) if baseline and baseline>p.price else None
    eligible = bool(p.affiliate_url and p.commission_rate > 0)
    score = calculate_score(p.price, p.original_price, p.commission_rate)
    return {"id":p.id,"marketplace":p.marketplace,"external_id":p.external_id,"title":p.title,"category":p.category,"price":p.price,"original_price":p.original_price,"commission_rate":p.commission_rate,"affiliate_url":p.affiliate_url,"affiliate_label":p.affiliate_label,"affiliate_source":p.affiliate_source,"image_url":p.image_url,"permalink":p.permalink,"source":p.source,"synced_at":p.synced_at.isoformat() if p.synced_at else None,"history_count":len(prices),"verified_discount_pct":verified_discount,"affiliate_ready":eligible,"score":score["score"] if eligible else None,"expected_commission":score["expected_commission"] if eligible else None}

@router.get("")
def list_products(q: str = "", marketplace: str = "", limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), db:Session=Depends(get_db)):
    stmt=select(Product)
    if q: stmt=stmt.where(Product.title.ilike(f"%{q[:100]}%"))
    if marketplace: stmt=stmt.where(Product.marketplace == marketplace)
    total=db.scalar(select(func.count()).select_from(stmt.subquery()))
    items=db.scalars(stmt.order_by(Product.id.desc()).limit(limit).offset(offset)).all()
    return {"items":[serialize(p,db) for p in items],"total":total,"limit":limit,"offset":offset}

@router.post("", dependencies=[Depends(require_admin)])
def create_product(data:ProductIn, db:Session=Depends(get_db)):
    if db.scalar(select(Product.id).where(Product.marketplace==data.marketplace,Product.external_id==data.external_id)):
        raise HTTPException(409,"Produto já cadastrado")
    obj=Product(**data.model_dump()); db.add(obj); db.flush(); db.add(ProductPrice(product_id=obj.id,price=obj.price));db.commit();db.refresh(obj);return serialize(obj,db)
