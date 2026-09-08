from psycopg_pool import ConnectionPool

from domain.ExtractionData import ExtractionData


def get_paragraphs(connection_pool: ConnectionPool, tenant: str, pdf_file_name: str) -> str:
    with connection_pool.connection() as connection:
        with connection.transaction():
            row = connection.execute(
                "SELECT data FROM paragraphs WHERE tenant = %s AND file_name = %s FOR UPDATE",
                (tenant, pdf_file_name),
            ).fetchone()
            if row is None:
                raise TypeError("No paragraphs")
            connection.execute("DELETE FROM paragraphs WHERE tenant = %s AND file_name = %s", (tenant, pdf_file_name))

    extraction_data = ExtractionData(**row[0])
    return extraction_data.model_dump_json()
