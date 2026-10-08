import json,re,secrets,hashlib,logging
from datetime import datetime,timedelta
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,EmailStr,Field
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.core.config import settings
from app.services.email_service import send_password_reset_email, EmailDeliveryError
from app.core.auth import (
    hash_password, verify_password, password_needs_rehash, verify_dummy_password,
    create_token, current_principal, require_role, Principal
)
from app.models.saas import Company,SaaSUser,CompanyMember,Plan,Subscription,AuditEvent,ContentAutomationProfile,GrowthEvent,UsageCounter,ContentAutomationRun,PasswordResetToken

logger=logging.getLogger(__name__)

router=APIRouter(prefix='/api/v1/saas',tags=['saas'])
class Register(BaseModel): name:str=Field(min_length=2,max_length=140);email:EmailStr;password:str=Field(min_length=8,max_length=128);company_name:str=Field(min_length=2,max_length=180);plan_code:str='ENTRY'
class Login(BaseModel): email:EmailStr;password:str
class ForgotPassword(BaseModel): email:EmailStr
class ResetPassword(BaseModel): token:str=Field(min_length=32,max_length=512);new_password:str=Field(min_length=8,max_length=128);password_confirmation:str=Field(min_length=8,max_length=128)
class ProfileUpdate(BaseModel): name:str=Field(min_length=2,max_length=140)
class PasswordChange(BaseModel): current_password:str;new_password:str=Field(min_length=8,max_length=128)
class MemberIn(BaseModel): email:EmailStr;name:str='';role:str='VIEWER'
class RoleIn(BaseModel): role:str
class ProfileIn(BaseModel): name:str='Autopilot padrão';enabled:bool=False;platforms:list[str]=['TikTok','Instagram'];tone:str='Direto e acessível';audience:str='';duration_seconds:int=30;daily_limit:int=3;require_human_approval:bool=True;min_opportunity_score:int=60

def slugify(s): return re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-')[:100] or 'empresa'
def audit(db,p,action,etype='',eid='',detail=None): db.add(AuditEvent(company_id=p.company_id,user_id=p.user_id,action=action,entity_type=etype,entity_id=str(eid),detail_json=json.dumps(detail or {},ensure_ascii=False)))
def ensure_plans(db):
    # Commercial plans. No free trial: ENTRY is the low-cost paid access tier.
    defaults=[
      ('ENTRY','Entrada',4900,{'users':2,'campaigns_month':20,'publications_month':10,'ai_text_month':30,'ai_video_month':0,'storage_mb':500}),
      ('STARTER','Starter',7900,{'users':2,'campaigns_month':60,'publications_month':40,'ai_text_month':100,'ai_video_month':2,'storage_mb':2048}),
      ('PRO','Pro',19900,{'users':5,'campaigns_month':300,'publications_month':200,'ai_text_month':500,'ai_video_month':10,'storage_mb':10240}),
      ('BUSINESS','Business',29900,{'users':15,'campaigns_month':1500,'publications_month':1000,'ai_text_month':2500,'ai_video_month':30,'storage_mb':51200}),
    ]
    wanted={x[0] for x in defaults}
    for code,name,price,limits in defaults:
        row=db.scalar(select(Plan).where(Plan.code==code))
        if not row:
            row=Plan(code=code,name=name,monthly_price_cents=price,currency='BRL',limits_json=json.dumps(limits),active=True)
            db.add(row)
        else:
            row.name=name; row.currency='BRL'; row.limits_json=json.dumps(limits); row.active=True
            # Migrate only the known legacy catalogue values. Afterwards the admin price is persistent.
            legacy={'ENTRY':2900,'STARTER':4900,'PRO':9900,'BUSINESS':19900}
            target={'ENTRY':4900,'STARTER':7900,'PRO':19900,'BUSINESS':29900}
            if row.monthly_price_cents==legacy.get(code): row.monthly_price_cents=target[code]
    # Historical TRIAL is retained only for referential safety and hidden from sale.
    trial=db.scalar(select(Plan).where(Plan.code=='TRIAL'))
    if trial: trial.active=False
    # One-time commercial transition: existing trial workspaces become ENTRY awaiting payment.
    for sub in db.scalars(select(Subscription).where(Subscription.plan_code=='TRIAL')).all():
        sub.plan_code='ENTRY';sub.status='incomplete';sub.trial_ends_at=None
        company=db.get(Company,sub.company_id)
        if company and company.status=='trial': company.status='pending_payment'
    db.commit()

@router.post('/auth/register')
def register(x:Register,db:Session=Depends(get_db)):
    if db.scalar(select(SaaSUser).where(func.lower(SaaSUser.email)==x.email.lower())): raise HTTPException(409,'E-mail já cadastrado')
    base=slugify(x.company_name);slug=base;n=1
    while db.scalar(select(Company).where(Company.slug==slug)): n+=1;slug=f'{base}-{n}'
    ensure_plans(db)
    plan_code=x.plan_code.upper().strip()
    if plan_code not in {'ENTRY','STARTER','PRO','BUSINESS'}: raise HTTPException(422,'Plano inválido')
    c=Company(name=x.company_name.strip(),slug=slug,status='pending_payment');u=SaaSUser(name=x.name.strip(),email=x.email.lower(),password_hash=hash_password(x.password))
    db.add_all([c,u]);db.flush();m=CompanyMember(company_id=c.id,user_id=u.id,role='OWNER');db.add(m)
    db.add(Subscription(company_id=c.id,plan_code=plan_code,status='incomplete',trial_ends_at=None))
    db.add(ContentAutomationProfile(company_id=c.id));db.add(GrowthEvent(company_id=c.id,user_id=u.id,event_name='signup_completed',source='product'));db.commit()
    return {'access_token':create_token(u.id,c.id,'OWNER'),'token_type':'bearer','company':{'id':c.id,'name':c.name,'slug':c.slug},'user':{'id':u.id,'name':u.name,'email':u.email,'role':'OWNER'}}

@router.post('/auth/login')
def login(x:Login,db:Session=Depends(get_db)):
    u=db.scalar(select(SaaSUser).where(func.lower(SaaSUser.email)==x.email.lower()))
    if not u:
        verify_dummy_password(x.password)
        raise HTTPException(401,'E-mail ou senha inválidos')
    if not verify_password(x.password,u.password_hash):
        raise HTTPException(401,'E-mail ou senha inválidos')
    m=db.scalar(select(CompanyMember).where(CompanyMember.user_id==u.id,CompanyMember.status=='active').order_by(CompanyMember.id))
    if not m: raise HTTPException(403,'Usuário sem empresa ativa')
    # Transparent migration: successful logins from old bcrypt accounts are
    # immediately re-hashed with Argon2id. No password reset is required.
    if password_needs_rehash(u.password_hash):
        u.password_hash=hash_password(x.password)
    u.last_login_at=datetime.utcnow();db.commit()
    return {'access_token':create_token(u.id,m.company_id,m.role),'token_type':'bearer'}

@router.post('/auth/forgot-password')
def forgot_password(x:ForgotPassword,db:Session=Depends(get_db)):
    # Always return the same public response to prevent account enumeration.
    public={'sent':True,'message':'Se existir uma conta com esse e-mail, enviaremos as instruções para redefinir a senha.'}
    u=db.scalar(select(SaaSUser).where(func.lower(SaaSUser.email)==x.email.lower()))
    if not u or not u.is_active:
        return public
    now=datetime.utcnow()
    # Invalidate earlier unused links before issuing a new one.
    old=db.scalars(select(PasswordResetToken).where(PasswordResetToken.user_id==u.id,PasswordResetToken.used_at.is_(None))).all()
    for item in old: item.used_at=now
    raw=secrets.token_urlsafe(48)
    digest=hashlib.sha256(raw.encode()).hexdigest()
    expires=now+timedelta(minutes=max(5,settings.password_reset_minutes))
    db.add(PasswordResetToken(user_id=u.id,token_hash=digest,expires_at=expires))
    db.commit()
    reset_url=f"{settings.frontend_url.rstrip('/')}/redefinir-senha?token={raw}"
    try:
        resend_id=send_password_reset_email(u.email,reset_url)
        logger.info('[PASSWORD_RESET] E-mail de recuperação enviado; user_id=%s; resend_id=%s', u.id, resend_id or 'n/d')
    except EmailDeliveryError as exc:
        # Never expose provider/configuration details to the public endpoint.
        # Log the internal reason and invalidate the token because no usable e-mail was delivered.
        logger.error('[PASSWORD_RESET] Falha no envio; user_id=%s; motivo=%s', u.id, exc)
        token=db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash==digest))
        if token:
            token.used_at=datetime.utcnow()
            db.commit()
    return public

@router.post('/auth/reset-password')
def reset_password(x:ResetPassword,db:Session=Depends(get_db)):
    if x.new_password!=x.password_confirmation:
        raise HTTPException(422,'As senhas não conferem')
    digest=hashlib.sha256(x.token.encode()).hexdigest()
    item=db.scalar(select(PasswordResetToken).where(PasswordResetToken.token_hash==digest))
    now=datetime.utcnow()
    if not item or item.used_at is not None or item.expires_at < now:
        raise HTTPException(400,'Link inválido ou expirado. Solicite uma nova redefinição de senha.')
    u=db.get(SaaSUser,item.user_id)
    if not u or not u.is_active:
        raise HTTPException(400,'Link inválido ou expirado. Solicite uma nova redefinição de senha.')
    u.password_hash=hash_password(x.new_password)
    # Consume every outstanding reset token for this user.
    outstanding=db.scalars(select(PasswordResetToken).where(PasswordResetToken.user_id==u.id,PasswordResetToken.used_at.is_(None))).all()
    for token in outstanding: token.used_at=now
    db.add(AuditEvent(company_id=None,user_id=u.id,action='security.password_reset',entity_type='user',entity_id=str(u.id),detail_json='{}'))
    db.commit()
    return {'saved':True,'message':'Senha redefinida com sucesso.'}

@router.get('/me')
def me(p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    u=db.get(SaaSUser,p.user_id);c=db.get(Company,p.company_id);s=db.scalar(select(Subscription).where(Subscription.company_id==p.company_id));ensure_plans(db);plan=db.scalar(select(Plan).where(Plan.code==(s.plan_code if s else 'ENTRY')))
    return {'user':{'id':u.id,'name':u.name,'email':u.email,'role':p.role},'company':{'id':c.id,'name':c.name,'slug':c.slug,'status':c.status},'subscription':{'plan':s.plan_code if s else 'ENTRY','status':s.status if s else 'incomplete','trial_ends_at':s.trial_ends_at.isoformat() if s and s.trial_ends_at else None,'limits':json.loads(plan.limits_json) if plan else {}}}

@router.patch('/profile')
def update_profile(x:ProfileUpdate,p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    u=db.get(SaaSUser,p.user_id)
    if not u: raise HTTPException(404,'Usuário não encontrado')
    u.name=x.name.strip();audit(db,p,'profile.updated','user',u.id);db.commit()
    return {'saved':True,'user':{'id':u.id,'name':u.name,'email':u.email,'role':p.role}}

@router.post('/security/password')
def change_password(x:PasswordChange,p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    u=db.get(SaaSUser,p.user_id)
    if not u or not verify_password(x.current_password,u.password_hash): raise HTTPException(400,'Senha atual inválida')
    if x.current_password==x.new_password: raise HTTPException(400,'A nova senha deve ser diferente da senha atual')
    u.password_hash=hash_password(x.new_password);audit(db,p,'security.password_changed','user',u.id);db.commit()
    return {'saved':True}

@router.get('/members')
def members(p:Principal=Depends(require_role('ADMIN')),db:Session=Depends(get_db)):
    rows=db.execute(select(CompanyMember,SaaSUser).join(SaaSUser,SaaSUser.id==CompanyMember.user_id).where(CompanyMember.company_id==p.company_id)).all()
    return [{'id':m.id,'name':u.name,'email':u.email,'role':m.role,'status':m.status} for m,u in rows]

@router.post('/members')
def add_member(x:MemberIn,p:Principal=Depends(require_role('ADMIN')),db:Session=Depends(get_db)):
    role=x.role.upper()
    if role not in {'ADMIN','EDITOR','VIEWER'}: raise HTTPException(422,'Perfil inválido')
    u=db.scalar(select(SaaSUser).where(func.lower(SaaSUser.email)==x.email.lower()))
    if not u: raise HTTPException(409,'O usuário precisa criar a conta antes de ser adicionado. Convites por e-mail entram na próxima etapa.')
    if db.scalar(select(CompanyMember).where(CompanyMember.company_id==p.company_id,CompanyMember.user_id==u.id)): raise HTTPException(409,'Usuário já pertence à empresa')
    m=CompanyMember(company_id=p.company_id,user_id=u.id,role=role);db.add(m);audit(db,p,'member.added','user',u.id,{'role':role});db.commit();return {'id':m.id,'role':m.role}

@router.patch('/members/{member_id}')
def change_role(member_id:int,x:RoleIn,p:Principal=Depends(require_role('OWNER')),db:Session=Depends(get_db)):
    m=db.get(CompanyMember,member_id)
    if not m or m.company_id!=p.company_id: raise HTTPException(404,'Membro não encontrado')
    role=x.role.upper()
    if role not in {'ADMIN','EDITOR','VIEWER'}: raise HTTPException(422,'Perfil inválido')
    m.role=role;audit(db,p,'member.role_changed','member',m.id,{'role':role});db.commit();return {'id':m.id,'role':m.role}

@router.get('/plans')
def plans(db:Session=Depends(get_db)):
    ensure_plans(db);rows=db.scalars(select(Plan).where(Plan.active==True).order_by(Plan.monthly_price_cents)).all()
    return [{'code':x.code,'name':x.name,'monthly_price_cents':x.monthly_price_cents,'currency':x.currency,'limits':json.loads(x.limits_json)} for x in rows]

@router.get('/onboarding')
def onboarding(p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    from app.models.entities import Product
    from app.models.social import SocialConnection,ContentCampaign,Publication
    from app.models.oauth import MercadoLivreOAuth
    integrations=db.scalars(select(SocialConnection).where(SocialConnection.company_id==p.company_id)).all()
    meli_connected=bool(db.scalar(select(MercadoLivreOAuth).where(MercadoLivreOAuth.company_id==p.company_id)))
    products=db.scalar(select(func.count(Product.id)).where(Product.company_id==p.company_id)) or 0
    campaigns=db.scalar(select(func.count(ContentCampaign.id)).where(ContentCampaign.company_id==p.company_id)) or 0
    publications=db.scalar(select(func.count(Publication.id)).where(Publication.company_id==p.company_id,Publication.status=='published')) or 0
    platforms={x.platform for x in integrations}
    sub=db.scalar(select(Subscription).where(Subscription.company_id==p.company_id))
    billing_active=bool(sub and sub.status in {'active','trialing'})
    steps=[
      {'key':'workspace','label':'Workspace criado','done':True,'href':'/dashboard'},
      {'key':'billing','label':'Ativar plano e cobrança','done':billing_active,'href':'/plano'},
      {'key':'marketplace','label':'Conectar Mercado Livre','done':meli_connected,'href':'/integracoes'},
      {'key':'social','label':'Conectar uma rede social','done':bool({x.lower() for x in platforms} & {'tiktok','pinterest','instagram','youtube shorts'}),'href':'/integracoes'},
      {'key':'product','label':'Adicionar primeiro produto','done':products>0,'href':'/produtos'},
      {'key':'content','label':'Criar primeiro conteúdo','done':campaigns>0,'href':'/conteudos'},
      {'key':'publish','label':'Fazer primeira publicação','done':publications>0,'href':'/conteudos'},
    ]
    completed=sum(1 for x in steps if x['done']);return {'steps':steps,'completed':completed,'total':len(steps),'percent':round(completed/len(steps)*100)}

@router.get('/usage')
def usage(p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    key=datetime.utcnow().strftime('%Y-%m');u=db.scalar(select(UsageCounter).where(UsageCounter.company_id==p.company_id,UsageCounter.period_key==key))
    s=db.scalar(select(Subscription).where(Subscription.company_id==p.company_id));ensure_plans(db);pl=db.scalar(select(Plan).where(Plan.code==(s.plan_code if s else 'ENTRY')));limits=json.loads(pl.limits_json) if pl else {}
    return {'period':key,'campaigns_created':u.campaigns_created if u else 0,'publications_created':u.publications_created if u else 0,'ai_generations':u.ai_generations if u else 0,'ai_video_generations':getattr(u,'ai_video_generations',0) if u else 0,'storage_bytes':u.storage_bytes if u else 0,'limits':limits}

@router.get('/automation-profile')
def get_profile(p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    x=db.scalar(select(ContentAutomationProfile).where(ContentAutomationProfile.company_id==p.company_id)) or ContentAutomationProfile(company_id=p.company_id);db.add(x);db.commit();db.refresh(x)
    return {'id':x.id,'name':x.name,'enabled':x.enabled,'platforms':x.platforms_csv.split(','),'tone':x.tone,'audience':x.audience,'duration_seconds':x.duration_seconds,'daily_limit':x.daily_limit,'require_human_approval':x.require_human_approval,'min_opportunity_score':x.min_opportunity_score}

@router.put('/automation-profile')
def save_profile(x:ProfileIn,p:Principal=Depends(require_role('EDITOR')),db:Session=Depends(get_db)):
    row=db.scalar(select(ContentAutomationProfile).where(ContentAutomationProfile.company_id==p.company_id)) or ContentAutomationProfile(company_id=p.company_id)
    row.name=x.name;row.enabled=x.enabled;row.platforms_csv=','.join(x.platforms);row.tone=x.tone;row.audience=x.audience;row.duration_seconds=x.duration_seconds;row.daily_limit=max(1,min(x.daily_limit,50));row.require_human_approval=True if x.require_human_approval else False;row.min_opportunity_score=max(0,min(x.min_opportunity_score,100));db.add(row);audit(db,p,'automation.updated','automation_profile',row.id,{'enabled':row.enabled});db.commit();return {'saved':True}

@router.get('/audit')
def audits(p:Principal=Depends(require_role('ADMIN')),db:Session=Depends(get_db)):
    rows=db.scalars(select(AuditEvent).where(AuditEvent.company_id==p.company_id).order_by(AuditEvent.id.desc()).limit(200)).all()
    return [{'id':x.id,'action':x.action,'entity_type':x.entity_type,'entity_id':x.entity_id,'detail':json.loads(x.detail_json or '{}'),'created_at':x.created_at.isoformat()} for x in rows]

@router.post('/automation/prepare')
def prepare_content(p:Principal=Depends(require_role('EDITOR')),db:Session=Depends(get_db)):
    from app.models.entities import Product
    from app.models.social import ContentCampaign, ContentVariant
    from app.routers.social import _variant, PLATFORMS
    from app.services.scoring import calculate_score
    profile=db.scalar(select(ContentAutomationProfile).where(ContentAutomationProfile.company_id==p.company_id))
    if not profile or not profile.enabled: raise HTTPException(409,'Ative a preparação automática antes de executar.')
    platforms=[x for x in profile.platforms_csv.split(',') if x in PLATFORMS]
    if not platforms: raise HTTPException(422,'Nenhuma plataforma válida configurada.')
    # Same live, explainable score used by Opportunities. No stale ProductScore dependency.
    candidates=[]
    for product in db.scalars(select(Product).where(Product.company_id==p.company_id,Product.affiliate_url!='',Product.commission_rate>0)).all():
        score=calculate_score(product.price,product.original_price,product.commission_rate)
        if score['score']>=profile.min_opportunity_score: candidates.append((product,score))
    rows=sorted(candidates,key=lambda x:x[1]['score'],reverse=True)[:profile.daily_limit]
    run=ContentAutomationRun(company_id=p.company_id,user_id=p.user_id,status='running',requested_count=profile.daily_limit);db.add(run);db.flush();created=[]
    for product,score in rows:
        c=ContentCampaign(company_id=p.company_id,product_id=product.id,name=product.title[:300],objective='Venda',format='Vídeo curto',duration_seconds=profile.duration_seconds,tone=profile.tone,audience=profile.audience,status='draft',origin='automation')
        db.add(c);db.flush()
        for platform in platforms:
            hook,caption,script,tags,cta=_variant(product,platform,profile.duration_seconds,profile.tone,profile.audience)
            db.add(ContentVariant(company_id=p.company_id,campaign_id=c.id,platform=platform,title=product.title[:300],hook=hook,caption=caption,script=script,hashtags=tags,cta=cta,affiliate_url=product.affiliate_url,affiliate_label=product.affiliate_label,link_placement='bio' if platform=='TikTok' else 'caption',status='draft'))
        created.append({'campaign_id':c.id,'product_id':product.id,'score':score['score'],'title':product.title})
    key=datetime.utcnow().strftime('%Y-%m');usage=db.scalar(select(UsageCounter).where(UsageCounter.company_id==p.company_id,UsageCounter.period_key==key)) or UsageCounter(company_id=p.company_id,period_key=key);usage.campaigns_created+=len(created);db.add(usage);run.status='completed';run.created_count=len(created);run.finished_at=datetime.utcnow();run.detail_json=json.dumps({'campaign_ids':[x['campaign_id'] for x in created]});audit(db,p,'automation.prepared','campaign','',{'count':len(created),'approval_required':profile.require_human_approval});db.commit()
    return {'created':len(created),'campaigns':created,'approval_required':profile.require_human_approval,'note':'Conteúdos preparados como rascunho; nenhuma publicação foi enviada automaticamente.'}

@router.post('/legacy/claim')
def claim_legacy_data(p:Principal=Depends(require_role('OWNER')),db:Session=Depends(get_db)):
    """One-time V1.8 -> V1.9 migration helper. Claims only rows with company_id IS NULL."""
    from app.models.entities import Product,ProductPrice,ProductScore,ProductContent
    from app.models.social import SocialConnection,SocialOAuthAttempt,ContentCampaign,ContentVariant,Publication
    from app.models.oauth import MercadoLivreOAuth,OAuthAttempt
    models=[Product,ProductPrice,ProductScore,ProductContent,SocialConnection,SocialOAuthAttempt,ContentCampaign,ContentVariant,Publication,MercadoLivreOAuth,OAuthAttempt]
    counts={}
    for model in models:
        if not hasattr(model,'company_id'):continue
        n=db.query(model).filter(model.company_id.is_(None)).update({model.company_id:p.company_id},synchronize_session=False)
        counts[model.__tablename__]=n
    audit(db,p,'legacy.claimed','company',p.company_id,counts);db.commit()
    return {'claimed':counts,'company_id':p.company_id,'note':'Somente registros legados sem empresa foram vinculados.'}
