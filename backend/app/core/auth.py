from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from fastapi import Depends, Header, HTTPException
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.db import get_db
from app.models.saas import SaaSUser, CompanyMember

pwd=CryptContext(schemes=['bcrypt'], deprecated='auto')
ALGO='HS256'

def hash_password(value:str)->str: return pwd.hash(value)
def verify_password(value:str, hashed:str)->bool: return pwd.verify(value,hashed)
def create_token(user_id:int,company_id:int,role:str)->str:
    now=datetime.now(timezone.utc)
    return jwt.encode({'sub':str(user_id),'company_id':company_id,'role':role,'iat':int(now.timestamp()),'exp':int((now+timedelta(hours=12)).timestamp())},settings.jwt_secret,algorithm=ALGO)

@dataclass
class Principal:
    user_id:int
    company_id:int
    role:str
    is_super_admin:bool=False

ROLE_LEVEL={'VIEWER':10,'EDITOR':20,'ADMIN':30,'OWNER':40}

def current_principal(authorization:str|None=Header(default=None),db:Session=Depends(get_db))->Principal:
    if not authorization or not authorization.lower().startswith('bearer '): raise HTTPException(401,'Autenticação necessária')
    try: payload=jwt.decode(authorization.split(' ',1)[1],settings.jwt_secret,algorithms=[ALGO])
    except JWTError: raise HTTPException(401,'Sessão inválida ou expirada')
    uid=int(payload.get('sub') or 0); cid=int(payload.get('company_id') or 0)
    user=db.get(SaaSUser,uid)
    member=db.scalar(select(CompanyMember).where(CompanyMember.user_id==uid,CompanyMember.company_id==cid,CompanyMember.status=='active'))
    if not user or not user.is_active or not member: raise HTTPException(401,'Acesso não autorizado')
    return Principal(uid,cid,member.role,user.is_super_admin)

def require_role(minimum:str):
    def dep(p:Principal=Depends(current_principal)):
        if not p.is_super_admin and ROLE_LEVEL.get(p.role,0)<ROLE_LEVEL[minimum]: raise HTTPException(403,'Permissão insuficiente')
        return p
    return dep
