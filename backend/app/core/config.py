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
    # pending_trial | trial | standard. Used only for UX/status; credentials still control OAuth.
    pinterest_access_status: str = "trial"
    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_redirect_uri: str = ""
    r2_endpoint_url: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = ""
    media_max_upload_mb: int = 500
    # OpenAI Content Studio
    openai_api_key: str = ""
    openai_text_model: str = "gpt-5.6-luna"
    openai_video_model: str = "sora-2"  # legado; não usado pelo provider fal
    # V1.13.2 - Video Provider
    video_provider: str = "fal"
    fal_key: str = ""
    fal_video_model: str = "fal-ai/kling-video/v3/standard/text-to-video"
    fal_image_video_model: str = "fal-ai/kling-video/v3/standard/image-to-video"
    # Comma-separated extra browser origins, e.g. https://app.example.com
    cors_origins: str = ""
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_entry: str = ""
    stripe_price_starter: str = ""
    stripe_price_pro: str = ""
    stripe_price_business: str = ""
    platform_admin_emails: str = ""
    # V1.13.3 - Transactional e-mail / password recovery
    resend_api_key: str = ""
    email_from: str = "AIAffiliateIntelligence <noreply@iaaffintel.com>"
    password_reset_minutes: int = 30
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

# Social publishing (V1.5)
# V1.10 commercial SaaS
