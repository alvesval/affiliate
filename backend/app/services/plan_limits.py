import json
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.saas import Subscription, Plan, UsageCounter


def _period_key() -> str:
    return datetime.utcnow().strftime('%Y-%m')


def get_plan_context(db: Session, company_id: int):
    sub = db.scalar(select(Subscription).where(Subscription.company_id == company_id))
    plan_code = (sub.plan_code if sub else 'ENTRY').upper()
    plan = db.scalar(select(Plan).where(Plan.code == plan_code))
    limits = json.loads(plan.limits_json or '{}') if plan else {}
    key = _period_key()
    usage = db.scalar(select(UsageCounter).where(UsageCounter.company_id == company_id, UsageCounter.period_key == key))
    if not usage:
        usage = UsageCounter(company_id=company_id, period_key=key)
        db.add(usage)
        db.flush()
    return sub, plan_code, limits, usage


def require_active_subscription(db: Session, company_id: int):
    sub, plan_code, limits, usage = get_plan_context(db, company_id)
    if not sub or sub.status not in {'active', 'trialing'}:
        raise HTTPException(402, 'Assinatura inativa. Ative um plano em Plano e assinatura para continuar.')
    return sub, plan_code, limits, usage


def enforce_monthly_limit(db: Session, company_id: int, limit_key: str, usage_field: str, increment: int = 1):
    sub, plan_code, limits, usage = require_active_subscription(db, company_id)
    limit = int(limits.get(limit_key, 0) or 0)
    used = int(getattr(usage, usage_field, 0) or 0)
    if limit <= 0:
        raise HTTPException(402, f'O plano {plan_code} não inclui este recurso. Faça upgrade em Plano e assinatura.')
    if used + increment > limit:
        raise HTTPException(402, f'Limite mensal atingido ({used}/{limit}). Faça upgrade do plano para continuar.')
    return usage, used, limit


def consume(usage: UsageCounter, usage_field: str, amount: int = 1):
    setattr(usage, usage_field, int(getattr(usage, usage_field, 0) or 0) + amount)
