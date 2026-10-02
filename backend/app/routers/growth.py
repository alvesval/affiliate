import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.auth import current_principal, Principal
from app.core.config import settings
from app.models.saas import GrowthEvent, Company, SaaSUser, Subscription, Referral, Plan

router=APIRouter(prefix='/api/v1/growth',tags=['growth'])

class TrackIn(BaseModel):
    event_name:str=Field(min_length=2,max_length=80)
    visitor_id:str='';session_id:str='';source:str='';medium:str='';campaign:str='';content:str='';term:str='';referrer:str='';landing_path:str='';metadata:dict={}

def _admin(p,db):
    u=db.get(SaaSUser,p.user_id)
    configured={x.strip().lower() for x in settings.platform_admin_emails.split(',') if x.strip()}
    if not p.is_super_admin and (not u or u.email.lower() not in configured): raise HTTPException(403,'Acesso restrito à administração da plataforma')
    return u

@router.post('/track')
def track(x:TrackIn, request:Request, db:Session=Depends(get_db)):
    # Public first-party event collector. Never accepts company/user ids from the browser.
    e=GrowthEvent(event_name=x.event_name,visitor_id=x.visitor_id[:120],session_id=x.session_id[:120],source=x.source[:120],medium=x.medium[:120],campaign=x.campaign[:180],content=x.content[:180],term=x.term[:180],referrer=x.referrer[:1000],landing_path=x.landing_path[:500],metadata_json=json.dumps(x.metadata,ensure_ascii=False)[:8000])
    db.add(e);db.commit();return {'accepted':True}

@router.get('/summary')
def summary(days:int=30,p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    _admin(p,db); days=max(7,min(days,365)); start=datetime.utcnow()-timedelta(days=days)
    events=db.scalars(select(GrowthEvent).where(GrowthEvent.created_at>=start)).all()
    counts={}
    sources={}
    for e in events:
        counts[e.event_name]=counts.get(e.event_name,0)+1
        src=e.source or 'direto'; sources[src]=sources.get(src,0)+1
    companies=db.scalar(select(func.count(Company.id)).where(Company.created_at>=start)) or 0
    active_subs=db.scalars(select(Subscription).where(Subscription.status.in_(['active','trialing']))).all()
    plans={x.code:x.monthly_price_cents for x in db.scalars(select(Plan)).all()}
    mrr=sum(plans.get(s.plan_code,0) for s in active_subs if s.status=='active')/100
    trials=sum(1 for s in active_subs if s.status=='trialing')
    paid=sum(1 for s in active_subs if s.status=='active')
    activated=counts.get('first_publication',0)
    signups=counts.get('signup_completed',0) or companies
    return {'period_days':days,'visitors':counts.get('landing_view',0),'signups':signups,'trials':trials,'activated':activated,'paid_companies':paid,'mrr':mrr,'churned':counts.get('subscription_canceled',0),'referrals':counts.get('referral_signup',0),'conversion_signup_pct':round(signups/max(counts.get('landing_view',0),1)*100,1),'activation_pct':round(activated/max(signups,1)*100,1),'paid_pct':round(paid/max(signups,1)*100,1),'sources':sorted([{'source':k,'events':v} for k,v in sources.items()],key=lambda x:x['events'],reverse=True)[:12],'funnel':counts}
