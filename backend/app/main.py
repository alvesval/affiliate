from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.db import Base, engine, SessionLocal
from app.models.entities import Product, ProductContent
from app.models.social import SocialConnection, SocialOAuthAttempt, ContentCampaign, ContentVariant, Publication
from app.models.oauth import MercadoLivreOAuth, OAuthAttempt
from app.models.saas import Company, SaaSUser, CompanyMember, Plan, Subscription, AuditEvent, ContentAutomationProfile, GrowthEvent, Referral, UsageCounter, ContentAutomationRun
from app.routers import mercadolivre
from app.routers import products, dashboard, catalog, content, affiliates, social, saas, growth, billing, ai_studio
from app.core.config import settings
app=FastAPI(title="Affiliate Intelligence API",version="1.12.0")
_default_origins=["http://localhost:3000","http://127.0.0.1:3000","https://affiliate.alvaldeir.workers.dev","https://iaaffintel.com","https://www.iaaffintel.com"]
_extra=[x.strip().rstrip('/') for x in settings.cors_origins.split(',') if x.strip()]
_origins=list(dict.fromkeys(_default_origins+_extra+[settings.frontend_url.rstrip('/')]))
app.add_middleware(CORSMiddleware,allow_origins=_origins,allow_credentials=True,allow_methods=["*"],allow_headers=["*"] )
from app.core.migrations import upgrade, upgrade_social, upgrade_saas, upgrade_tenant_stage2, upgrade_tenant_constraints, upgrade_v112
upgrade(engine)
upgrade_social(engine)
upgrade_saas(engine)
upgrade_tenant_stage2(engine)
upgrade_tenant_constraints(engine)
upgrade_v112(engine)
Base.metadata.create_all(bind=engine)
@app.get("/health")
def health(): return {"status":"ok","version":"1.12.0","ai_video_configured":bool(settings.openai_api_key and settings.openai_video_model),"stripe_configured":bool(settings.stripe_secret_key)}
app.include_router(products.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(mercadolivre.router)

app.include_router(catalog.router)
app.include_router(content.router)
app.include_router(affiliates.router)

app.include_router(social.router)
app.include_router(ai_studio.router)

app.include_router(saas.router)
app.include_router(growth.router)
app.include_router(billing.router)
