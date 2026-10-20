import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine,select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.core.db import Base,get_db
from app.core.auth import current_principal,Principal
from app.core.config import settings
from app.routers.support import router
from app.models.saas import Company,SaaSUser,AuditEvent
from app.models.social import ContentCampaign
from app.models.support import SupportTicket,SupportMessage,SupportRead

@pytest.fixture
def ctx():
 engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
 Base.metadata.create_all(engine)
 db=Session(engine)
 db.add_all([Company(id=1,name='Empresa A',slug='a'),Company(id=2,name='Empresa B',slug='b'),
  SaaSUser(id=1,name='Cliente A',email='a@test.local',password_hash='unused'),
  SaaSUser(id=2,name='Cliente B',email='b@test.local',password_hash='unused'),
  SaaSUser(id=3,name='Atendente',email='staff@test.local',password_hash='unused'),
  SaaSUser(id=4,name='Colega A',email='colega@test.local',password_hash='unused')]);db.commit()
 app=FastAPI();app.include_router(router)
 p=Principal(1,1,'VIEWER',False)
 app.dependency_overrides[current_principal]=lambda:p
 app.dependency_overrides[get_db]=lambda:db
 yield TestClient(app),db,p
 db.close();engine.dispose()

def create(c,**data):
 return c.post('/api/v1/support/tickets',json={'subject':'Falha ao publicar','category':'technical','message':'Preciso de ajuda para publicar.',**data})
def staff(p):p.user_id=3;p.company_id=2;p.is_super_admin=True

def test_inactive_customer_create_and_complete_conversation(ctx):
 c,db,p=ctx
 # No subscription exists: support must remain accessible.
 r=create(c);assert r.status_code==201,r.text
 t=r.json();assert t['protocol']=='SUP-000001'
 staff(p)
 assert c.get('/api/v1/support/unread').json()['admin']==1
 assert c.get('/api/v1/support/admin/tickets').json()['total']==1
 assert c.post('/api/v1/support/admin/tickets/1/messages',json={'body':'Vamos verificar.'}).status_code==201
 assert db.get(SupportTicket,1).status=='waiting_customer'
 p.user_id=1;p.company_id=1;p.is_super_admin=False
 d=c.get('/api/v1/support/tickets/1').json();assert len(d['messages'])==2
 assert c.get('/api/v1/support/unread').json()['customer']==1
 assert c.post('/api/v1/support/tickets/1/read',json={'last_message_id':d['last_message_id']}).status_code==200
 assert c.get('/api/v1/support/unread').json()['customer']==0
 assert c.patch('/api/v1/support/tickets/1',json={'status':'resolved'}).status_code==200
 assert c.post('/api/v1/support/tickets/1/messages',json={'body':'Ainda não resolveu.'}).status_code==201
 assert db.get(SupportTicket,1).status=='open'
 assert db.scalar(select(AuditEvent).where(AuditEvent.action=='support_ticket_created'))

@pytest.mark.parametrize('method,path,payload',[('get','',None),('post','/messages',{'body':'Tentativa'}),('patch','',{'status':'resolved'}),('post','/read',{'last_message_id':1})])
def test_cross_company_access_denied(ctx,method,path,payload):
 c,db,p=ctx;create(c);p.user_id=2;p.company_id=2
 r=getattr(c,method)('/api/v1/support/tickets/1'+path,**({'json':payload} if payload else {}))
 assert r.status_code==404
 assert c.get('/api/v1/support/tickets').json()['total']==0
 assert c.get('/api/v1/support/unread').json()['customer']==0

@pytest.mark.parametrize('method,path,payload',[('get','',None),('get','/1',None),('post','/1/messages',{'body':'Teste'}),('patch','/1',{'status':'resolved'}),('post','/1/read',{'last_message_id':1})])
def test_owner_is_not_platform_staff(ctx,method,path,payload):
 c,db,p=ctx;create(c);p.role='OWNER'
 assert getattr(c,method)('/api/v1/support/admin/tickets'+path,**({'json':payload} if payload else {})).status_code==403

def test_notes_are_private_and_cannot_be_forged(ctx):
 c,db,p=ctx;create(c)
 assert c.post('/api/v1/support/tickets/1/messages',json={'body':'Segredo','internal':True}).status_code==403
 staff(p)
 r=c.post('/api/v1/support/admin/tickets/1/messages',json={'body':'Observação confidencial','internal':True});assert r.status_code==201
 note=r.json()['id'];assert db.get(SupportTicket,1).status=='open'
 assert len(c.get('/api/v1/support/admin/tickets/1').json()['messages'])==2
 p.user_id=1;p.company_id=1;p.is_super_admin=False
 assert len(c.get('/api/v1/support/tickets/1').json()['messages'])==1
 assert c.get('/api/v1/support/unread').json()['customer']==0
 assert c.post('/api/v1/support/tickets/1/read',json={'last_message_id':note}).status_code==422
 assert c.patch('/api/v1/support/tickets/1',json={'priority':'urgent'}).status_code==403
 assert c.patch('/api/v1/support/tickets/1',json={'status':'in_progress'}).status_code==403

def test_read_receipts_are_per_user_monotonic_and_do_not_swallow_new_messages(ctx):
 c,db,p=ctx;create(c);staff(p)
 c.post('/api/v1/support/admin/tickets/1/messages',json={'body':'Primeira resposta'})
 p.user_id=1;p.company_id=1;p.is_super_admin=False
 seen=c.get('/api/v1/support/tickets/1').json()['last_message_id']
 staff(p);c.post('/api/v1/support/admin/tickets/1/messages',json={'body':'Segunda resposta'})
 p.user_id=1;p.company_id=1;p.is_super_admin=False
 c.post('/api/v1/support/tickets/1/read',json={'last_message_id':seen})
 assert c.get('/api/v1/support/unread').json()['customer']==1
 c.post('/api/v1/support/tickets/1/read',json={'last_message_id':1})
 assert c.get('/api/v1/support/unread').json()['customer']==1
 p.user_id=4
 assert c.get('/api/v1/support/unread').json()['customer']==3

def test_staff_management_filters_pagination_and_search(ctx):
 c,db,p=ctx;create(c);create(c,subject='Pagamento pendente',category='billing')
 staff(p)
 assert c.patch('/api/v1/support/admin/tickets/1',json={'status':'in_progress','priority':'high'}).status_code==200
 assert c.get('/api/v1/support/admin/tickets?priority=high&status=in_progress').json()['total']==1
 assert c.get('/api/v1/support/admin/tickets?category=billing').json()['total']==1
 assert c.get('/api/v1/support/admin/tickets?q=SUP-000001').json()['items'][0]['id']==1
 assert c.get('/api/v1/support/admin/tickets?q=Empresa%20A').json()['total']==2
 assert c.get('/api/v1/support/admin/tickets?limit=1&offset=1').json()['total']==2
 assert len(c.get('/api/v1/support/admin/tickets?limit=1&offset=1').json()['items'])==1
 assert c.get('/api/v1/support/admin/tickets?q=%25').json()['total']==0

@pytest.mark.parametrize('data',[{'subject':'   '},{'message':'   '},{'category':'invalid'},{'message':'x'*10001},{'campaign_id':999}])
def test_input_validation(ctx,data):
 c,db,p=ctx
 assert create(c,**data).status_code==422
 assert db.scalar(select(SupportTicket)) is None

def test_server_ignores_forged_company_priority_and_staff_flag(ctx):
 c,db,p=ctx
 r=create(c,company_id=2,requester_id=3,priority='urgent',status='resolved',internal=True)
 assert r.status_code==201
 t=db.get(SupportTicket,1);assert (t.company_id,t.requester_id,t.priority,t.status)==(1,1,'normal','open')
 m=db.scalar(select(SupportMessage));assert not m.internal and not m.author_is_staff

def test_admin_email_configuration_is_honored(ctx,monkeypatch):
 c,db,p=ctx;create(c);p.user_id=3;p.company_id=2
 monkeypatch.setattr(settings,'platform_admin_emails','staff@test.local')
 assert c.get('/api/v1/support/admin/tickets').status_code==200
