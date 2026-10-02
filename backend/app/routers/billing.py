import json
from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy import select
from sqlalchemy.orm import Session
import stripe
from app.core.db import get_db
from app.core.auth import require_role, current_principal, Principal
from app.core.config import settings
from app.models.saas import Subscription,Plan,Company,GrowthEvent

router=APIRouter(prefix='/api/v1/billing',tags=['billing'])

def _price(plan): return {'STARTER':settings.stripe_price_starter,'PRO':settings.stripe_price_pro,'BUSINESS':settings.stripe_price_business}.get(plan,'')

@router.post('/checkout/{plan_code}')
def checkout(plan_code:str,p:Principal=Depends(require_role('OWNER')),db:Session=Depends(get_db)):
    plan_code=plan_code.upper(); price=_price(plan_code)
    if not settings.stripe_secret_key or not price: raise HTTPException(503,'Checkout ainda não configurado para este plano')
    stripe.api_key=settings.stripe_secret_key
    s=db.scalar(select(Subscription).where(Subscription.company_id==p.company_id)); c=db.get(Company,p.company_id)
    kwargs={'mode':'subscription','line_items':[{'price':price,'quantity':1}],'success_url':settings.frontend_url+'/plano?checkout=success','cancel_url':settings.frontend_url+'/plano?checkout=cancel','client_reference_id':str(p.company_id),'metadata':{'company_id':str(p.company_id),'plan_code':plan_code}}
    if s and s.provider_customer_id: kwargs['customer']=s.provider_customer_id
    session=stripe.checkout.Session.create(**kwargs)
    return {'url':session.url}

@router.post('/portal')
def portal(p:Principal=Depends(require_role('OWNER')),db:Session=Depends(get_db)):
    s=db.scalar(select(Subscription).where(Subscription.company_id==p.company_id))
    if not settings.stripe_secret_key or not s or not s.provider_customer_id: raise HTTPException(409,'Cliente de cobrança ainda não disponível')
    stripe.api_key=settings.stripe_secret_key
    session=stripe.billing_portal.Session.create(customer=s.provider_customer_id,return_url=settings.frontend_url+'/plano')
    return {'url':session.url}

@router.post('/webhook')
async def webhook(request:Request,db:Session=Depends(get_db)):
    if not settings.stripe_secret_key or not settings.stripe_webhook_secret: raise HTTPException(503,'Webhook não configurado')
    stripe.api_key=settings.stripe_secret_key
    payload=await request.body(); sig=request.headers.get('stripe-signature','')
    try: event=stripe.Webhook.construct_event(payload,sig,settings.stripe_webhook_secret)
    except Exception: raise HTTPException(400,'Assinatura do webhook inválida')
    obj=event['data']['object']; typ=event['type']
    if typ=='checkout.session.completed':
        cid=int((obj.get('metadata') or {}).get('company_id') or obj.get('client_reference_id') or 0); plan=(obj.get('metadata') or {}).get('plan_code','PRO')
        s=db.scalar(select(Subscription).where(Subscription.company_id==cid))
        if s:
            s.provider='stripe';s.provider_customer_id=obj.get('customer') or '';s.provider_subscription_id=obj.get('subscription') or '';s.plan_code=plan;s.status='active'
            db.add(GrowthEvent(company_id=cid,event_name='subscription_started',source='stripe',metadata_json=json.dumps({'plan':plan})))
    elif typ in ('customer.subscription.updated','customer.subscription.deleted'):
        sid=obj.get('id');s=db.scalar(select(Subscription).where(Subscription.provider_subscription_id==sid))
        if s:
            status=obj.get('status','');s.status='canceled' if typ.endswith('deleted') else status
            if typ.endswith('deleted'): db.add(GrowthEvent(company_id=s.company_id,event_name='subscription_canceled',source='stripe'))
    db.commit();return {'received':True}
