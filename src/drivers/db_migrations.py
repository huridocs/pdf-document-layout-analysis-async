from psycopg_pool import ConnectionPool

MIGRATIONS = [
    # Retention: paragraphs carry the time their (re)-generation finished so old rows can be swept.
    "ALTER TABLE paragraphs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()",
]


def run_migrations(connection_pool: ConnectionPool) -> None:
    with connection_pool.connection() as connection:
        for migration in MIGRATIONS:
            connection.execute(migration)
        connection.commit()
