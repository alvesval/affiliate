from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.core.db import get_db
from app.models.entities import Product
from app.models.social import Publication
from app.services.scoring import calculate_score
from app.core.auth import current_principal, Principal

router=APIRouter(prefix="/dashboard",tags=["dashboard"])

@router.get("/summary")
def summary(principal:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    products=db.scalars(select(Product).where(Product.company_id==principal.company_id)).all()
    ranked=[]
    for product in products:
        if not product.affiliate_url or product.commission_rate<=0:
            continue
        score=calculate_score(product.price,product.original_price,product.commission_rate)
        ranked.append({"id":product.id,"title":product.title,"marketplace":product.marketplace,"price":product.price,**score})
    ranked.sort(key=lambda x:x["score"],reverse=True)
    publications=db.scalars(select(Publication).where(Publication.company_id==principal.company_id)).all()
    published=sum(1 for x in publications if x.status=="published")
    queued=sum(1 for x in publications if x.status in {"queued","pending","processing"})
    failed=sum(1 for x in publications if x.status in {"failed","error"})
    return {
        "products":len(products),
        "opportunities":len(ranked),
        "potential_commission":None,
        "marketplaces":len(set(x.marketplace for x in products)),
        "publications":len(publications),
        "published":published,
        "queued":queued,
        "failed":failed,
        "top":ranked[:5],
    }
