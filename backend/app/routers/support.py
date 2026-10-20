"""Customer support and platform staff inbox. No paid-plan dependency."""
import json
from datetime import datetime
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.db import get_db
from app.core.auth import Principal, current_principal
from app.routers.growth import _admin
from app.models.saas import Company, SaaSUser, AuditEvent
from app.models.social import ContentCampaign
from app.models.support import SupportTicket, SupportMessage, SupportRead

router = APIRouter(prefix='/api/v1/support', tags=['support'])
Category = Literal['billing','integrations','campaigns','technical','suggestion']
Status = Literal['open','in_progress','waiting_customer','resolved']
Priority = Literal['low','normal','high','urgent']

class TicketIn(BaseModel):
    subject: str = Field(min_length=3,max_length=180)
    category: Category
    message: str = Field(min_length=3,max_length=10000)
    campaign_id: int | None = Field(default=None,gt=0)
    @field_validator('subject','message')
    @classmethod
    def clean(cls,value):
        value=value.strip()
        if len(value)<3: raise ValueError('Informe pelo menos 3 caracteres.')
        return value

class MessageIn(BaseModel):
    body: str = Field(min_length=1,max_length=10000)
    internal: bool = False
    @field_validator('body')
    @classmethod
    def clean(cls,value):
        value=value.strip()
        if not value: raise ValueError('Escreva a mensagem.')
        return value

class TicketPatch(BaseModel):
    status: Status | None = None
    priority: Priority | None = None

class ReadIn(BaseModel):
    last_message_id: int = Field(ge=0)


def ticket_for(db,p,ticket_id,staff=False,lock=False):
    if staff: _admin(p,db)
    query=select(SupportTicket).where(SupportTicket.id==ticket_id)
    if not staff: query=query.where(SupportTicket.company_id==p.company_id)
    if lock: query=query.with_for_update()
    ticket=db.scalar(query)
    if not ticket: raise HTTPException(404,'Chamado não encontrado.')
    return ticket


def visible_messages(ticket_id,staff):
    query=select(SupportMessage).where(SupportMessage.ticket_id==ticket_id)
    if not staff: query=query.where(SupportMessage.internal.is_(False))
    return query


def unread_query(p,staff):
    query=(select(func.count(SupportMessage.id)).join(SupportTicket,SupportTicket.id==SupportMessage.ticket_id)
        .outerjoin(SupportRead,(SupportRead.ticket_id==SupportTicket.id)&(SupportRead.user_id==p.user_id))
        .where(SupportMessage.author_id!=p.user_id,
               SupportMessage.id>func.coalesce(SupportRead.last_message_id,0)))
    if not staff: query=query.where(SupportTicket.company_id==p.company_id,SupportMessage.internal.is_(False))
    return query


def row_json(ticket,db,p,staff=False):
    requester=db.get(SaaSUser,ticket.requester_id)
    company=db.get(Company,ticket.company_id)
    unread=db.scalar(unread_query(p,staff).where(SupportTicket.id==ticket.id)) or 0
    return {'id':ticket.id,'protocol':f'SUP-{ticket.id:06d}','subject':ticket.subject,
        'category':ticket.category,'priority':ticket.priority,'status':ticket.status,
        'campaign_id':ticket.campaign_id,'company_id':ticket.company_id,
        'company_name':company.name if company else '',
        'requester_name':requester.name if requester else '',
        'requester_email':requester.email if requester and staff else '',
        'created_at':ticket.created_at.isoformat()+'Z','updated_at':ticket.updated_at.isoformat()+'Z',
        'unread':unread}


def audit(db,p,ticket,action,details):
    db.add(AuditEvent(company_id=ticket.company_id,user_id=p.user_id,action=action,
        entity_type='support_ticket',entity_id=str(ticket.id),detail_json=json.dumps(details,ensure_ascii=False)))


def list_tickets(db,p,staff,status,category,priority,q,offset,limit):
    if staff: _admin(p,db)
    filters=[] if staff else [SupportTicket.company_id==p.company_id]
    if status: filters.append(SupportTicket.status==status)
    if category: filters.append(SupportTicket.category==category)
    if priority: filters.append(SupportTicket.priority==priority)
    if q:
        term=q.strip()
        choices=[SupportTicket.subject.contains(term,autoescape=True)]
        numeric=term.upper().removeprefix('SUP-')
        if numeric.isdigit(): choices.append(SupportTicket.id==int(numeric))
        if staff:
            choices.extend([SupportTicket.company_id.in_(select(Company.id).where(Company.name.contains(term,autoescape=True))),
                SupportTicket.requester_id.in_(select(SaaSUser.id).where(SaaSUser.email.contains(term,autoescape=True)))])
        filters.append(or_(*choices))
    total=db.scalar(select(func.count(SupportTicket.id)).where(*filters)) or 0
    rows=db.scalars(select(SupportTicket).where(*filters).order_by(SupportTicket.updated_at.desc(),SupportTicket.id.desc()).offset(offset).limit(limit)).all()
    return {'items':[row_json(x,db,p,staff) for x in rows],'total':total,'offset':offset,'limit':limit}

@router.get('/unread')
def unread(p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    customer=db.scalar(unread_query(p,False)) or 0
    try: _admin(p,db)
    except HTTPException as exc:
        if exc.status_code!=403: raise
        return {'customer':customer,'admin':0}
    return {'customer':customer,'admin':db.scalar(unread_query(p,True)) or 0}

@router.get('/tickets')
def customer_list(status:Status|None=None,category:Category|None=None,priority:Priority|None=None,
                  q:str=Query('',max_length=180),offset:int=Query(0,ge=0),limit:int=Query(30,ge=1,le=100),
                  p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    return list_tickets(db,p,False,status,category,priority,q,offset,limit)

@router.get('/admin/tickets')
def admin_list(status:Status|None=None,category:Category|None=None,priority:Priority|None=None,
               q:str=Query('',max_length=180),offset:int=Query(0,ge=0),limit:int=Query(30,ge=1,le=100),
               p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    return list_tickets(db,p,True,status,category,priority,q,offset,limit)

@router.post('/tickets',status_code=201)
def create(data:TicketIn,p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    if data.campaign_id and not db.scalar(select(ContentCampaign.id).where(
        ContentCampaign.id==data.campaign_id,ContentCampaign.company_id==p.company_id)):
        raise HTTPException(422,'Campanha não encontrada nesta empresa.')
    ticket=SupportTicket(company_id=p.company_id,requester_id=p.user_id,subject=data.subject,
        category=data.category,campaign_id=data.campaign_id)
    db.add(ticket);db.flush()
    db.add(SupportMessage(ticket_id=ticket.id,author_id=p.user_id,body=data.message,author_is_staff=False))
    audit(db,p,ticket,'support_ticket_created',{'category':data.category})
    db.commit()
    return row_json(ticket,db,p)


def detail(ticket_id,p,db,staff):
    ticket=ticket_for(db,p,ticket_id,staff)
    messages=db.scalars(visible_messages(ticket.id,staff).order_by(SupportMessage.id)).all()
    result=row_json(ticket,db,p,staff)
    result['messages']=[{'id':m.id,'body':m.body,'internal':m.internal,'staff':m.author_is_staff,
        'author_name':('Suporte' if m.author_is_staff else (db.get(SaaSUser,m.author_id).name if db.get(SaaSUser,m.author_id) else 'Usuário')),
        'created_at':m.created_at.isoformat()+'Z','own':m.author_id==p.user_id} for m in messages]
    result['last_message_id']=messages[-1].id if messages else 0
    return result

@router.get('/tickets/{ticket_id}')
def customer_detail(ticket_id:int,p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    return detail(ticket_id,p,db,False)

@router.get('/admin/tickets/{ticket_id}')
def admin_detail(ticket_id:int,p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    return detail(ticket_id,p,db,True)


def send(ticket_id,data,p,db,staff):
    ticket=ticket_for(db,p,ticket_id,staff,lock=True)
    if data.internal and not staff: raise HTTPException(403,'Observações internas são exclusivas do atendimento.')
    message=SupportMessage(ticket_id=ticket.id,author_id=p.user_id,body=data.body,
        author_is_staff=staff,internal=data.internal)
    db.add(message);db.flush()
    old_status=ticket.status
    if not data.internal:
        ticket.status='waiting_customer' if staff else ('open' if ticket.status in {'resolved','waiting_customer'} else ticket.status)
    ticket.updated_at=datetime.utcnow()
    audit(db,p,ticket,'support_message_sent',{'message_id':message.id,'internal':data.internal,'before_status':old_status,'after_status':ticket.status})
    db.commit()
    return {'id':message.id,'status':ticket.status}

@router.post('/tickets/{ticket_id}/messages',status_code=201)
def customer_send(ticket_id:int,data:MessageIn,p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    return send(ticket_id,data,p,db,False)

@router.post('/admin/tickets/{ticket_id}/messages',status_code=201)
def admin_send(ticket_id:int,data:MessageIn,p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    return send(ticket_id,data,p,db,True)


def patch(ticket_id,data,p,db,staff):
    ticket=ticket_for(db,p,ticket_id,staff,lock=True)
    if not staff and (data.priority is not None or data.status not in {'open','resolved'}):
        raise HTTPException(403,'O cliente pode apenas resolver ou reabrir o chamado.')
    before={'status':ticket.status,'priority':ticket.priority}
    if data.status is not None: ticket.status=data.status
    if data.priority is not None: ticket.priority=data.priority
    ticket.updated_at=datetime.utcnow()
    audit(db,p,ticket,'support_ticket_updated',{'before':before,'after':{'status':ticket.status,'priority':ticket.priority}})
    db.commit()
    return row_json(ticket,db,p,staff)

@router.patch('/tickets/{ticket_id}')
def customer_patch(ticket_id:int,data:TicketPatch,p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    return patch(ticket_id,data,p,db,False)

@router.patch('/admin/tickets/{ticket_id}')
def admin_patch(ticket_id:int,data:TicketPatch,p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    return patch(ticket_id,data,p,db,True)


def mark_read(ticket_id,data,p,db,staff):
    ticket_for(db,p,ticket_id,staff)
    if data.last_message_id and not db.scalar(visible_messages(ticket_id,staff).where(SupportMessage.id==data.last_message_id)):
        raise HTTPException(422,'Mensagem não encontrada neste chamado.')
    row=db.scalar(select(SupportRead).where(SupportRead.ticket_id==ticket_id,SupportRead.user_id==p.user_id).with_for_update())
    if row: row.last_message_id=max(row.last_message_id,data.last_message_id)
    else: db.add(SupportRead(ticket_id=ticket_id,user_id=p.user_id,last_message_id=data.last_message_id))
    try: db.commit()
    except IntegrityError:
        db.rollback()
        row=db.scalar(select(SupportRead).where(SupportRead.ticket_id==ticket_id,SupportRead.user_id==p.user_id).with_for_update())
        if not row: raise
        row.last_message_id=max(row.last_message_id,data.last_message_id);db.commit()
    return {'read':True}

@router.post('/tickets/{ticket_id}/read')
def customer_read(ticket_id:int,data:ReadIn,p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    return mark_read(ticket_id,data,p,db,False)

@router.post('/admin/tickets/{ticket_id}/read')
def admin_read(ticket_id:int,data:ReadIn,p:Principal=Depends(current_principal),db:Session=Depends(get_db)):
    return mark_read(ticket_id,data,p,db,True)
