import json
from datetime import datetime, timezone
from fastapi import APIRouter,Depends,HTTPException,Request
from sqlalchemy import select
from sqlalchemy.orm import Session
import stripe
from app.core.db import get_db
from app.core.auth import require_role, current_principal, Principal
from app.core.config import settings
from app.models.saas import Subscription,Plan,Company,GrowthEvent,SaaSUser

router=APIRouter(prefix='/api/v1/billing',tags=['billing'])
webhook_router=APIRouter(tags=['billing'])

def _prices():
    return {'ENTRY':settings.stripe_price_entry,'STARTER':settings.stripe_price_starter,'PRO':settings.stripe_price_pro,'BUSINESS':settings.stripe_price_business}
def _price(plan,db=None):
    if db:
        row=db.scalar(select(Plan).where(Plan.code==plan))
        if row and row.stripe_price_id: return row.stripe_price_id
    return _prices().get(plan,'')
def _plan_from_price(price_id,db=None):
    if db and price_id:
        row=db.scalar(select(Plan).where(Plan.stripe_price_id==price_id))
        if row: return row.code
    return next((code for code,pid in _prices().items() if pid and pid==price_id),None)
def _dt(ts):
    return datetime.fromtimestamp(ts,tz=timezone.utc).replace(tzinfo=None) if ts else None

def _stripe_ready():
    return bool(settings.stripe_secret_key)

@router.get('/status')
def billing_status(p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    s=db.scalar(select(Subscription).where(Subscription.company_id==p.company_id))
    return {'configured':_stripe_ready(),'webhook_configured':bool(settings.stripe_webhook_secret),'plan':s.plan_code if s else 'ENTRY','status':s.status if s else 'incomplete','customer_ready':bool(s and s.provider_customer_id),'portal_ready':bool(settings.stripe_secret_key and s and s.provider_customer_id)}

@router.post('/checkout/{plan_code}')
def checkout(plan_code:str,p:Principal=Depends(require_role('OWNER')),db:Session=Depends(get_db)):
    plan_code=plan_code.upper().strip(); price=_price(plan_code,db)
    if plan_code not in _prices(): raise HTTPException(422,'Plano inválido')
    if not settings.stripe_secret_key: raise HTTPException(503,'STRIPE_SECRET_KEY não configurada no backend')
    if not price: raise HTTPException(503,f'Price ID do plano {plan_code} não configurado. Use STRIPE_PRICE_{plan_code}=price_...')
    if not price.startswith('price_'): raise HTTPException(503,f'Configuração inválida para {plan_code}: o Stripe Checkout exige Price ID price_..., não Product ID prod_...')
    stripe.api_key=settings.stripe_secret_key
    s=db.scalar(select(Subscription).where(Subscription.company_id==p.company_id)); c=db.get(Company,p.company_id); u=db.get(SaaSUser,p.user_id)
    kwargs={'mode':'subscription','line_items':[{'price':price,'quantity':1}],
      'success_url':settings.frontend_url.rstrip('/')+'/plano?checkout=success&session_id={CHECKOUT_SESSION_ID}',
      'cancel_url':settings.frontend_url.rstrip('/')+'/plano?checkout=cancel',
      'client_reference_id':str(p.company_id),'metadata':{'company_id':str(p.company_id),'plan_code':plan_code},
      'subscription_data':{'metadata':{'company_id':str(p.company_id),'plan_code':plan_code}},
      'allow_promotion_codes':True}
    if s and s.provider_customer_id: kwargs['customer']=s.provider_customer_id
    elif u and u.email: kwargs['customer_email']=u.email
    try: session=stripe.checkout.Session.create(**kwargs)
    except stripe.StripeError as e: raise HTTPException(502,f'Stripe recusou o Checkout: {getattr(e,"user_message",None) or str(e)}')
    return {'url':session.url,'session_id':session.id}

@router.post('/portal')
def portal(p:Principal=Depends(require_role('OWNER')),db:Session=Depends(get_db)):
    s=db.scalar(select(Subscription).where(Subscription.company_id==p.company_id))
    if not settings.stripe_secret_key: raise HTTPException(503,'STRIPE_SECRET_KEY não configurada')
    if not s or not s.provider_customer_id: raise HTTPException(409,'Cliente Stripe ainda não disponível. Conclua uma assinatura primeiro.')
    stripe.api_key=settings.stripe_secret_key
    try: session=stripe.billing_portal.Session.create(customer=s.provider_customer_id,return_url=settings.frontend_url.rstrip('/')+'/plano')
    except stripe.StripeError as e: raise HTTPException(502,f'Não foi possível abrir o portal Stripe: {getattr(e,"user_message",None) or str(e)}')
    return {'url':session.url}

def _platform_admin(p,db):
    u=db.get(SaaSUser,p.user_id)
    configured={x.strip().lower() for x in settings.platform_admin_emails.split(',') if x.strip()}
    if not p.is_super_admin and (not u or u.email.lower() not in configured):
        raise HTTPException(403,'Acesso restrito à administração da plataforma')
    return u

@router.get('/admin/plans')
def admin_plans(p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    _platform_admin(p,db)
    rows=db.scalars(select(Plan).order_by(Plan.monthly_price_cents)).all()
    return [{'code':x.code,'name':x.name,'monthly_price_cents':x.monthly_price_cents,'currency':x.currency,'active':x.active,'stripe_price_id':x.stripe_price_id,'stripe_product_id':x.stripe_product_id,'limits':json.loads(x.limits_json or '{}')} for x in rows if x.code!='TRIAL']

@router.put('/admin/plans/{plan_code}')
def update_plan_price(plan_code:str,request_data:dict,p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    _platform_admin(p,db)
    code=plan_code.upper().strip(); row=db.scalar(select(Plan).where(Plan.code==code))
    if not row or code=='TRIAL': raise HTTPException(404,'Plano não encontrado')
    try: cents=int(request_data.get('monthly_price_cents'))
    except Exception: raise HTTPException(422,'Preço mensal inválido')
    if cents < 100: raise HTTPException(422,'Preço mensal deve ser de pelo menos R$ 1,00')
    create_stripe=bool(request_data.get('create_stripe_price',True))
    old_price=row.stripe_price_id or _prices().get(code,'')
    new_price_id=old_price; product_id=row.stripe_product_id
    if create_stripe:
        if not settings.stripe_secret_key: raise HTTPException(503,'STRIPE_SECRET_KEY não configurada')
        stripe.api_key=settings.stripe_secret_key
        try:
            if not product_id and old_price:
                old=stripe.Price.retrieve(old_price); product_id=str(old.get('product') or '')
            if not product_id:
                product=stripe.Product.create(name=f'AIAffiliateIntelligence {row.name}',metadata={'plan_code':code}); product_id=product.id
            price=stripe.Price.create(product=product_id,unit_amount=cents,currency='brl',recurring={'interval':'month'},metadata={'plan_code':code})
            new_price_id=price.id
        except stripe.StripeError as e:
            raise HTTPException(502,f'Não foi possível criar o novo preço no Stripe: {getattr(e,"user_message",None) or str(e)}')
    row.monthly_price_cents=cents; row.stripe_price_id=new_price_id or ''; row.stripe_product_id=product_id or ''
    db.commit()
    return {'saved':True,'code':code,'monthly_price_cents':cents,'stripe_price_id':row.stripe_price_id,'stripe_product_id':row.stripe_product_id,'previous_stripe_price_id':old_price}

@router.post('/webhook')
@webhook_router.post('/billing/webhook/stripe')
async def webhook(request:Request,db:Session=Depends(get_db)):
    if not settings.stripe_secret_key or not settings.stripe_webhook_secret: raise HTTPException(503,'Webhook Stripe não configurado')
    stripe.api_key=settings.stripe_secret_key
    payload=await request.body(); sig=request.headers.get('stripe-signature','')
    try: event=stripe.Webhook.construct_event(payload,sig,settings.stripe_webhook_secret)
    except Exception: raise HTTPException(400,'Assinatura do webhook inválida')
    obj=event['data']['object']; typ=event['type']
    if typ=='checkout.session.completed':
        cid=int((obj.get('metadata') or {}).get('company_id') or obj.get('client_reference_id') or 0); plan=(obj.get('metadata') or {}).get('plan_code','ENTRY')
        s=db.scalar(select(Subscription).where(Subscription.company_id==cid))
        if s:
            s.provider='stripe';s.provider_customer_id=obj.get('customer') or '';s.provider_subscription_id=obj.get('subscription') or '';s.plan_code=plan;s.status='active'
            company=db.get(Company,cid)
            if company: company.status='active'
            db.add(GrowthEvent(company_id=cid,event_name='subscription_started',source='stripe',metadata_json=json.dumps({'plan':plan})))
    elif typ in ('customer.subscription.created','customer.subscription.updated','customer.subscription.deleted'):
        sid=obj.get('id');s=db.scalar(select(Subscription).where(Subscription.provider_subscription_id==sid))
        if not s:
            cid=int((obj.get('metadata') or {}).get('company_id') or 0)
            if cid: s=db.scalar(select(Subscription).where(Subscription.company_id==cid))
        if s:
            s.provider='stripe';s.provider_customer_id=obj.get('customer') or s.provider_customer_id;s.provider_subscription_id=sid or s.provider_subscription_id
            items=((obj.get('items') or {}).get('data') or []); price_id=((items[0].get('price') or {}).get('id') if items else '')
            mapped=_plan_from_price(price_id,db) or (obj.get('metadata') or {}).get('plan_code')
            if mapped: s.plan_code=mapped
            status=obj.get('status','');s.status='canceled' if typ.endswith('deleted') else status;s.current_period_end=_dt(obj.get('current_period_end'))
            company=db.get(Company,s.company_id)
            if company: company.status='active' if status in ('active','trialing') and typ!='customer.subscription.deleted' else 'suspended'
            if typ.endswith('deleted'): db.add(GrowthEvent(company_id=s.company_id,event_name='subscription_canceled',source='stripe'))
    elif typ=='invoice.payment_failed':
        customer=obj.get('customer');s=db.scalar(select(Subscription).where(Subscription.provider_customer_id==customer))
        if s:
            s.status='past_due'; company=db.get(Company,s.company_id)
            if company: company.status='past_due'
            db.add(GrowthEvent(company_id=s.company_id,event_name='payment_failed',source='stripe'))
    elif typ=='invoice.paid':
        customer=obj.get('customer');s=db.scalar(select(Subscription).where(Subscription.provider_customer_id==customer))
        if s:
            if s.status not in ('canceled','unpaid'): s.status='active'
            company=db.get(Company,s.company_id)
            if company: company.status='active'
    db.commit();return {'received':True}
