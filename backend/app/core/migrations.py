"""Small idempotent transition from the existing V1 schema. Use Alembic for later releases."""
from sqlalchemy import inspect, text

def upgrade(engine):
    inspector = inspect(engine)
    if "products" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("products")}
    additions = {
        "image_url": "VARCHAR(2000) NOT NULL DEFAULT ''",
        "permalink": "VARCHAR(2000) NOT NULL DEFAULT ''",
        "source": "VARCHAR(40) NOT NULL DEFAULT 'manual'",
        "synced_at": "TIMESTAMP NULL",
        "affiliate_label": "VARCHAR(120) NOT NULL DEFAULT ''",
        "affiliate_source": "VARCHAR(40) NOT NULL DEFAULT ''",
        "affiliate_verified_at": "TIMESTAMP NULL",
    }
    with engine.begin() as conn:
        for name, ddl in additions.items():
            if name not in columns:
                conn.execute(text(f"ALTER TABLE products ADD COLUMN {name} {ddl}"))
        # Existing V1 rows can contain duplicates; avoid imposing a unique constraint
        # on pre-existing data until a deduplication migration has been reviewed.


def _add_columns(engine, table, additions):
    inspector=inspect(engine)
    if table not in inspector.get_table_names(): return
    columns={col["name"] for col in inspector.get_columns(table)}
    with engine.begin() as conn:
        for name,ddl in additions.items():
            if name not in columns: conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))

def upgrade_social(engine):
    _add_columns(engine,"content_variants",{
        "media_storage_key":"VARCHAR(1000) NOT NULL DEFAULT ''",
        "media_filename":"VARCHAR(500) NOT NULL DEFAULT ''",
        "media_content_type":"VARCHAR(100) NOT NULL DEFAULT ''",
        "media_size":"INTEGER NOT NULL DEFAULT 0",
        "media_duration_seconds":"INTEGER NOT NULL DEFAULT 0",
        "affiliate_url":"VARCHAR(1000) NOT NULL DEFAULT ''",
        "affiliate_label":"VARCHAR(120) NOT NULL DEFAULT ''",
        "link_placement":"VARCHAR(40) NOT NULL DEFAULT 'bio'",
        "affiliate_configured_at":"TIMESTAMP NULL",
    })
    _add_columns(engine,"publications",{
        "privacy_level":"VARCHAR(50) NOT NULL DEFAULT 'SELF_ONLY'",
        "disable_comment":"BOOLEAN NOT NULL DEFAULT FALSE",
        "disable_duet":"BOOLEAN NOT NULL DEFAULT FALSE",
        "disable_stitch":"BOOLEAN NOT NULL DEFAULT FALSE",
        "user_consent":"BOOLEAN NOT NULL DEFAULT FALSE",
        "brand_content_toggle":"BOOLEAN NOT NULL DEFAULT FALSE",
        "brand_organic_toggle":"BOOLEAN NOT NULL DEFAULT FALSE",
        "is_aigc":"BOOLEAN NOT NULL DEFAULT FALSE",
        "tiktok_status":"VARCHAR(80) NOT NULL DEFAULT ''",
        "tiktok_fail_reason":"TEXT NOT NULL DEFAULT ''",
        "uploaded_bytes":"INTEGER NOT NULL DEFAULT 0",
        "public_post_ids":"TEXT NOT NULL DEFAULT ''",
    })

def upgrade_saas(engine):
    # Transitional V1.9 tenant columns. Existing legacy rows remain NULL and can be assigned
    # after the first company is created; new SaaS endpoints always scope by company.
    for table in ('social_connections','social_oauth_attempts','content_campaigns','content_variants','publications','product_contents'):
        _add_columns(engine,table,{'company_id':'INTEGER NULL'})

def upgrade_tenant_stage2(engine):
    """V1.9 stage 2: tenant columns on all business/OAuth records."""
    for table in ('products','product_prices','product_scores','meli_oauth_attempts','meli_oauth_tokens'):
        _add_columns(engine, table, {'company_id':'INTEGER NULL'})
    if engine.dialect.name == 'postgresql':
        with engine.begin() as conn:
            rows=conn.execute(text("""SELECT tc.constraint_name FROM information_schema.table_constraints tc JOIN information_schema.constraint_column_usage ccu ON tc.constraint_name=ccu.constraint_name AND tc.table_schema=ccu.table_schema WHERE tc.table_schema=current_schema() AND tc.table_name='social_connections' AND tc.constraint_type='UNIQUE' AND ccu.column_name='platform'""")).fetchall()
            for (name,) in rows:
                safe=''.join(ch for ch in name if ch.isalnum() or ch=='_')
                conn.execute(text(f'ALTER TABLE social_connections DROP CONSTRAINT IF EXISTS {safe}'))

def upgrade_tenant_constraints(engine):
    if engine.dialect.name != 'postgresql': return
    with engine.begin() as conn:
        conn.execute(text('ALTER TABLE products DROP CONSTRAINT IF EXISTS uq_product_marketplace_external'))
        conn.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS uq_product_company_marketplace_external_idx ON products(company_id, marketplace, external_id) WHERE company_id IS NOT NULL'))
        conn.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS uq_social_connection_company_platform_idx ON social_connections(company_id, platform) WHERE company_id IS NOT NULL'))
        conn.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS uq_meli_oauth_company_idx ON meli_oauth_tokens(company_id) WHERE company_id IS NOT NULL'))


def upgrade_v112(engine):
    _add_columns(engine,"usage_counters",{
        "ai_video_generations":"INTEGER NOT NULL DEFAULT 0",
    })


def upgrade_v113(engine):
    _add_columns(engine,"plans",{
        "stripe_price_id":"VARCHAR(180) NOT NULL DEFAULT ''",
        "stripe_product_id":"VARCHAR(180) NOT NULL DEFAULT ''",
    })
