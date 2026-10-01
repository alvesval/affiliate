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
