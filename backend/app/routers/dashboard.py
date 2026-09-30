from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.db import get_db
from app.models.entities import Product
from app.services.scoring import calculate_score
router=APIRouter(prefix="/dashboard",tags=["dashboard"])
@router.get("/summary")
def summary(db:Session=Depends(get_db)):
    products=db.scalars(select(Product)).all()
    ranked=[]
    for p in products:
        if not p.affiliate_url or p.commission_rate<=0: continue
        s=calculate_score(p.price,p.original_price,p.commission_rate)
        ranked.append({"id":p.id,"title":p.title,"marketplace":p.marketplace,"price":p.price,**s})
    ranked.sort(key=lambda x:x["score"],reverse=True)
    return {"products":len(products),"opportunities":len(ranked),"potential_commission":None,"marketplaces":len(set(p.marketplace for p in products)),"top":ranked[:5]}
