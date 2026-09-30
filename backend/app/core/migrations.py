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
