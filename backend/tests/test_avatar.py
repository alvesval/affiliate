import sys,io
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from PIL import Image
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine,select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.core.db import Base,get_db
from app.core.auth import Principal,current_principal
from app.routers import saas
from app.models.avatar import UserAvatar
from app.models.saas import Company,SaaSUser,AuditEvent
from app.services.avatar_image import normalize_avatar,MAX_UPLOAD

def image_bytes(fmt='PNG',size=(500,300)):
 b=io.BytesIO();Image.new('RGB',size,'blue').save(b,format=fmt);return b.getvalue()

@pytest.fixture
def ctx():
 engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
 Base.metadata.create_all(engine);db=Session(engine)
 db.add_all([Company(id=1,name='Empresa',slug='empresa'),SaaSUser(id=1,email='a@test.dev',name='Cliente A',password_hash='unused'),SaaSUser(id=2,email='b@test.dev',name='Cliente B',password_hash='unused')]);db.commit()
 p=Principal(1,1,'OWNER');app=FastAPI();app.include_router(saas.router);app.dependency_overrides[get_db]=lambda:db;app.dependency_overrides[current_principal]=lambda:p
 yield TestClient(app),db,p
 db.close();engine.dispose()

@pytest.mark.parametrize('fmt',['JPEG','PNG','WEBP'])
def test_avatar_formats_are_normalized(fmt):
 result=Image.open(io.BytesIO(normalize_avatar(image_bytes(fmt))))
 assert result.size==(256,256) and result.format=='JPEG' and result.mode=='RGB'

@pytest.mark.parametrize('data',[b'<svg></svg>',b'not an image',b'x'*(MAX_UPLOAD+1),image_bytes('GIF')])
def test_invalid_images(data):
 with pytest.raises(ValueError):normalize_avatar(data)

def test_alpha_background_and_metadata():
 b=io.BytesIO();Image.new('RGBA',(20,20),(0,0,0,0)).save(b,format='PNG')
 result=Image.open(io.BytesIO(normalize_avatar(b.getvalue())))
 assert result.getpixel((5,5))==(255,255,255) and not result.getexif()

def test_upload_read_me_isolation_and_delete(ctx):
 c,db,p=ctx
 r=c.post('/api/v1/saas/profile/avatar',files={'file':('foto.png',image_bytes(),'image/png')});assert r.status_code==200,r.text
 version=r.json()['avatar_version'];assert version
 r=c.get('/api/v1/saas/profile/avatar');assert r.headers['content-type']=='image/jpeg'
 assert 'no-store' in r.headers['cache-control']
 assert c.get('/api/v1/saas/me').json()['user']['avatar_version']==version
 p.user_id=2
 assert c.get('/api/v1/saas/profile/avatar').status_code==404
 assert c.delete('/api/v1/saas/profile/avatar').status_code==200
 assert db.get(UserAvatar,1) is not None
 p.user_id=1
 assert c.delete('/api/v1/saas/profile/avatar').status_code==200
 assert c.get('/api/v1/saas/profile/avatar').status_code==404
 assert c.get('/api/v1/saas/me').json()['user']['avatar_version']==''
 assert db.scalar(select(AuditEvent).where(AuditEvent.action=='profile.avatar_updated'))

def test_invalid_upload_does_not_replace_valid_avatar(ctx):
 c,db,p=ctx
 c.post('/api/v1/saas/profile/avatar',files={'file':('foto.png',image_bytes(),'image/png')})
 before=db.get(UserAvatar,1).version
 r=c.post('/api/v1/saas/profile/avatar',files={'file':('foto.png',b'invalid','image/png')})
 assert r.status_code==422 and db.get(UserAvatar,1).version==before
