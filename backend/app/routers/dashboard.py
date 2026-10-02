from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.db import get_db
from app.models.entities import Product
from app.services.scoring import calculate_score
from app.core.auth import current_principal, Principal
router=APIRouter(prefix="/dashboard",tags=["dashboard"])
@router.get("/summary")
def summary(p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    products=db.scalars(select(Product).where(Product.company_id==p.company_id)).all()
    ranked=[]
    for p in products:
        if not p.affiliate_url or p.commission_rate<=0: continue
        s=calculate_score(p.price,p.original_price,p.commission_rate)
        ranked.append({"id":p.id,"title":p.title,"marketplace":p.marketplace,"price":p.price,**s})
    ranked.sort(key=lambda x:x["score"],reverse=True)
    return {"products":len(products),"opportunities":len(ranked),"potential_commission":None,"marketplaces":len(set(p.marketplace for p in products)),"top":ranked[:5]}
