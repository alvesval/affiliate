from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "sqlite:///./affiliate.db"
    jwt_secret: str = "dev-secret"
    admin_setup_key: str = ""
    meli_client_id: str = ""
    meli_client_secret: str = ""
    meli_redirect_uri: str = ""
    token_encryption_key: str = ""
    frontend_url: str = "http://localhost:3000"
    tiktok_client_key: str = ""
    tiktok_client_secret: str = ""
    tiktok_redirect_uri: str = ""
    youtube_client_id: str = ""
    youtube_client_secret: str = ""
    youtube_redirect_uri: str = ""
    pinterest_client_id: str = ""
    pinterest_client_secret: str = ""
    pinterest_redirect_uri: str = ""
    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_redirect_uri: str = ""
    r2_endpoint_url: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = ""
    media_max_upload_mb: int = 500
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_starter: str = ""
    stripe_price_pro: str = ""
    stripe_price_business: str = ""
    platform_admin_emails: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

# Social publishing (V1.5)
# V1.10 commercial SaaS
