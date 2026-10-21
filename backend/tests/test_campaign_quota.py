from test_rc6 import ctx
import json
import pytest
from sqlalchemy import select
from app.models.saas import UsageCounter, Subscription, AuditEvent, Plan
from app.models.social import ContentCampaign,ContentVariant
from app.services.plan_limits import enforce_monthly_limit

def reset(client,current_period,**changes):
 data={'campaigns_created':0,'expected_used':20,'period':current_period,'reason':'Testes administrativos'}
 return client.put('/api/v1/growth/admin/clients/1/campaign-usage',json={**data,**changes})

def full_usage(db):
 u=db.scalar(select(UsageCounter).where(UsageCounter.company_id==1));u.campaigns_created=20
 plan=db.scalar(select(Plan).where(Plan.code=='ENTRY'));plan.limits_json=json.dumps({'campaigns_month':20,'publications_month':10});db.commit();return u

def test_reset_campaigns_releases_limit_and_preserves_everything_else(ctx):
 c,db,p,period=ctx;u=full_usage(db)
 before=len(db.scalars(select(ContentCampaign)).all())
 r=reset(c,period);assert r.status_code==200,r.text
 assert r.json()['released']==20 and r.json()['campaigns_created']==0
 _,used,limit=enforce_monthly_limit(db,1,'campaigns_month','campaigns_created');assert (used,limit)==(0,20)
 assert (u.publications_created,u.ai_generations)==(10,7)
 assert len(db.scalars(select(ContentCampaign)).all())==before
 assert db.get(ContentVariant,1).caption=='Legenda'
 sub=db.scalar(select(Subscription));assert (sub.plan_code,sub.provider_customer_id,sub.provider_subscription_id)==('ENTRY','cus_keep','sub_keep')
 other=db.scalar(select(UsageCounter).where(UsageCounter.company_id==2));assert other.publications_created==8
 event=db.scalar(select(AuditEvent).where(AuditEvent.action=='campaign_usage_adjusted'))
 assert json.loads(event.detail_json)['after']==0

@pytest.mark.parametrize('changes,status',[({'campaigns_created':-1},422),({'campaigns_created':21},422),({'campaigns_created':0.1},422),({'expected_used':19},409),({'period':'1999-01'},409),({'reason':'   '},422)])
def test_invalid_campaign_reset_keeps_consumption(ctx,changes,status):
 c,db,p,period=ctx;u=full_usage(db)
 assert reset(c,period,**changes).status_code==status
 assert u.campaigns_created==20

def test_workspace_owner_cannot_reset_campaigns(ctx):
 c,db,p,period=ctx;u=full_usage(db);p.user_id=2;p.is_super_admin=False
 assert reset(c,period).status_code==403
 assert u.campaigns_created==20
