from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.db import Base, engine, SessionLocal
from app.models.entities import Product, ProductContent
from app.models.social import SocialConnection, SocialOAuthAttempt, ContentCampaign, ContentVariant, Publication
from app.models.oauth import MercadoLivreOAuth, OAuthAttempt
from app.routers import mercadolivre
from app.routers import products, dashboard, catalog, content, affiliates, social
app=FastAPI(title="Affiliate Intelligence API",version="1.5.0")
app.add_middleware(CORSMiddleware,allow_origins=["http://localhost:3000"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"] )
from app.core.migrations import upgrade
upgrade(engine)
Base.metadata.create_all(bind=engine)
@app.get("/health")
def health(): return {"status":"ok","version":"1.5.0"}
app.include_router(products.router, prefix="/api/v1")
app.include_router(dashboard.router, prefix="/api/v1")
app.include_router(mercadolivre.router)

app.include_router(catalog.router)
app.include_router(content.router)
app.include_router(affiliates.router)

app.include_router(social.router)
