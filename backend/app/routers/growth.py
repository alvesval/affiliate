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

@router.get('/admin/access')
def admin_access(p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    u=_admin(p,db)
    return {'is_platform_admin':True,'email':u.email if u else ''}

@router.get('/admin/clients')
def admin_clients(p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    _admin(p,db)
    from app.models.saas import CompanyMember, UsageCounter
    from app.models.entities import Product
    from app.models.social import ContentCampaign, Publication
    companies=db.scalars(select(Company).order_by(Company.created_at.desc())).all()
    result=[]
    for c in companies:
        sub=db.scalar(select(Subscription).where(Subscription.company_id==c.id))
        owner_member=db.scalar(select(CompanyMember).where(CompanyMember.company_id==c.id,CompanyMember.role=='OWNER').order_by(CompanyMember.id))
        owner=db.get(SaaSUser,owner_member.user_id) if owner_member else None
        result.append({
            'id':c.id,'name':c.name,'slug':c.slug,'status':c.status,'created_at':c.created_at.isoformat(),
            'owner':{'name':owner.name if owner else '', 'email':owner.email if owner else ''},
            'plan':sub.plan_code if sub else 'ENTRY','subscription_status':sub.status if sub else 'incomplete',
            'products':db.scalar(select(func.count(Product.id)).where(Product.company_id==c.id)) or 0,
            'campaigns':db.scalar(select(func.count(ContentCampaign.id)).where(ContentCampaign.company_id==c.id)) or 0,
            'publications':db.scalar(select(func.count(Publication.id)).where(Publication.company_id==c.id)) or 0,
        })
    return result

@router.get('/admin/clients/{company_id}')
def admin_client_detail(company_id:int,p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    _admin(p,db)
    from app.models.saas import CompanyMember, UsageCounter
    from app.models.entities import Product
    from app.models.social import ContentCampaign, Publication, SocialConnection
    c=db.get(Company,company_id)
    if not c: raise HTTPException(404,'Cliente não encontrado')
    sub=db.scalar(select(Subscription).where(Subscription.company_id==company_id))
    plan=db.scalar(select(Plan).where(Plan.code==(sub.plan_code if sub else 'ENTRY')))
    members=db.scalars(select(CompanyMember).where(CompanyMember.company_id==company_id,CompanyMember.status=='active')).all()
    users=[]
    for m in members:
        u=db.get(SaaSUser,m.user_id)
        if u: users.append({'id':u.id,'name':u.name,'email':u.email,'role':m.role,'last_login_at':u.last_login_at.isoformat() if u.last_login_at else None})
    products=db.scalars(select(Product).where(Product.company_id==company_id).order_by(Product.id.desc()).limit(50)).all()
    product_rows=[]
    for x in products:
        campaigns=db.scalar(select(func.count(ContentCampaign.id)).where(ContentCampaign.company_id==company_id,ContentCampaign.product_id==x.id)) or 0
        product_rows.append({'id':x.id,'title':x.title,'marketplace':x.marketplace,'category':x.category,'price':x.price,'campaigns':campaigns})
    pubs=db.scalars(select(Publication).where(Publication.company_id==company_id)).all()
    platform_usage={}
    status_usage={}
    for x in pubs:
        platform_usage[x.platform]=platform_usage.get(x.platform,0)+1
        status_usage[x.status]=status_usage.get(x.status,0)+1
    period=datetime.utcnow().strftime('%Y-%m')
    usage=db.scalar(select(UsageCounter).where(UsageCounter.company_id==company_id,UsageCounter.period_key==period))
    connections=db.scalars(select(SocialConnection).where(SocialConnection.company_id==company_id)).all()
    campaigns_total=db.scalar(select(func.count(ContentCampaign.id)).where(ContentCampaign.company_id==company_id)) or 0
    publications_total=len(pubs)
    usage_now={'campaigns_created':usage.campaigns_created if usage else 0,'publications_created':usage.publications_created if usage else 0,'ai_generations':usage.ai_generations if usage else 0,'ai_video_generations':usage.ai_video_generations if usage else 0,'storage_bytes':usage.storage_bytes if usage else 0}
    return {
      'company':{'id':c.id,'name':c.name,'slug':c.slug,'status':c.status,'created_at':c.created_at.isoformat()},
      'subscription':{'plan':sub.plan_code if sub else 'ENTRY','status':sub.status if sub else 'incomplete','current_period_end':sub.current_period_end.isoformat() if sub and sub.current_period_end else None,'monthly_price_cents':plan.monthly_price_cents if plan else 0,'limits':json.loads(plan.limits_json or '{}') if plan else {}},
      'users':users,'products':product_rows,
      'usage':usage_now,'totals':{'products':len(product_rows),'campaigns':campaigns_total,'publications':publications_total,'users':len(users)},
      'platform_usage':platform_usage,'publication_status':status_usage,
      'connections':[{'platform':x.platform,'account_name':x.account_name,'connected_at':x.connected_at.isoformat()} for x in connections],
    }
