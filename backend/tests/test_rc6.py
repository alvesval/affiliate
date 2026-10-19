import sys, json
from pathlib import Path
from datetime import datetime
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine,select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.core.db import Base,get_db
from app.core.auth import current_principal,Principal
from app.routers import growth,social
from app.models.saas import Company,SaaSUser,UsageCounter,AuditEvent,Subscription,Plan
from app.models.social import ContentCampaign,ContentVariant,Publication
from app.models.entities import Product
from app.services.plan_limits import enforce_monthly_limit

@pytest.fixture
def ctx():
 engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
 Base.metadata.create_all(engine)
 db=Session(engine)
 period=datetime.utcnow().strftime('%Y-%m')
 db.add_all([Company(id=1,name='Cliente',slug='cliente'),Company(id=2,name='Outro',slug='outro'),
  SaaSUser(id=1,email='admin@test.local',name='Admin',password_hash='unused'),
  SaaSUser(id=2,email='owner@test.local',name='Owner',password_hash='unused'),
  UsageCounter(company_id=1,period_key=period,publications_created=10,campaigns_created=4,ai_generations=7),
  UsageCounter(company_id=2,period_key=period,publications_created=8),
  Plan(code='ENTRY',name='Entrada',limits_json=json.dumps({'publications_month':10})),
  Subscription(company_id=1,plan_code='ENTRY',status='active',provider='stripe',provider_customer_id='cus_keep',provider_subscription_id='sub_keep'),
  Product(id=1,company_id=1,marketplace='manual',external_id='1',title='Produto',affiliate_url='https://example.com'),
  ContentCampaign(id=1,company_id=1,product_id=1,name='Campanha',status='approved'),
  ContentCampaign(id=2,company_id=2,product_id=1,name='Outra',status='draft'),
  ContentVariant(id=1,company_id=1,campaign_id=1,platform='Pinterest',title='Título',hook='Gancho',script='Roteiro',caption='Legenda',status='approved'),
 ])
 db.commit()
 app=FastAPI();app.include_router(growth.router);app.include_router(social.router)
 principal=Principal(1,1,'OWNER',True)
 app.dependency_overrides[get_db]=lambda:db
 app.dependency_overrides[current_principal]=lambda:principal
 yield TestClient(app),db,principal,period
 db.close();engine.dispose()

def adjustment(client,current_period,**kwargs):
 data=dict(publications_created=0,expected_used=10,period=current_period,reason='Testes de integração')
 return client.put('/api/v1/growth/admin/clients/1/publication-usage',json={**data,**kwargs})

def test_reset_releases_quota_and_preserves_billing_history(ctx):
 client,db,p,period=ctx
 db.add(Publication(company_id=1,campaign_id=1,variant_id=1,platform='Pinterest',status='published'));db.commit()
 r=adjustment(client,period);assert r.status_code==200,r.text
 assert r.json()['released']==10
 usage,used,limit=enforce_monthly_limit(db,1,'publications_month','publications_created')
 assert (used,limit,usage.campaigns_created,usage.ai_generations)==(0,10,4,7)
 sub=db.scalar(select(Subscription));assert (sub.plan_code,sub.provider_customer_id,sub.provider_subscription_id)==('ENTRY','cus_keep','sub_keep')
 assert len(db.scalars(select(Publication)).all())==1
 assert db.scalar(select(UsageCounter).where(UsageCounter.company_id==2)).publications_created==8
 audit=db.scalar(select(AuditEvent));assert json.loads(audit.detail_json)['before']==10

def test_normal_owner_cannot_reset(ctx):
 client,db,p,period=ctx;p.user_id=2;p.is_super_admin=False
 assert adjustment(client,period).status_code==403
 assert db.scalar(select(UsageCounter).where(UsageCounter.company_id==1)).publications_created==10

@pytest.mark.parametrize('data,code', [({'publications_created':-1},422),({'publications_created':11},422),({'publications_created':1.5},422),({'reason':'   '},422),({'period':'1999-01'},409),({'expected_used':9},409)])
def test_invalid_or_stale_adjustments(ctx,data,code):
 client,db,p,period=ctx
 assert adjustment(client,period,**data).status_code==code
 assert db.scalar(select(UsageCounter).where(UsageCounter.company_id==1)).publications_created==10

def campaign_data():
 return dict(name='Campanha corrigida',objective='Venda',format='Vídeo curto',duration_seconds=30,tone='Informativo',audience='Famílias')

def test_campaign_edit_preserves_texts_and_requires_approval(ctx):
 client,db,p,period=ctx
 r=client.put('/api/v1/social/campaigns/1',json=campaign_data());assert r.status_code==200,r.text
 assert r.json()['name']=='Campanha corrigida' and r.json()['status']=='draft'
 assert r.json()['variants'][0]['caption']=='Legenda'
 assert db.get(ContentVariant,1).status=='draft'
 assert db.scalar(select(UsageCounter).where(UsageCounter.company_id==1)).campaigns_created==4

@pytest.mark.parametrize('status',['queued','scheduled','processing','published','sent_to_tiktok'])
def test_cannot_change_campaign_with_active_publication(ctx,status):
 client,db,p,period=ctx
 db.add(Publication(company_id=1,campaign_id=1,variant_id=1,platform='Pinterest',status=status));db.commit()
 assert client.put('/api/v1/social/campaigns/1',json=campaign_data()).status_code==409
 assert db.get(ContentCampaign,1).name=='Campanha'

def test_campaign_tenant_and_viewer_permissions(ctx):
 client,db,p,period=ctx;p.is_super_admin=False;p.user_id=2
 assert client.put('/api/v1/social/campaigns/2',json=campaign_data()).status_code==404
 p.role='VIEWER'
 assert client.put('/api/v1/social/campaigns/1',json=campaign_data()).status_code==403
