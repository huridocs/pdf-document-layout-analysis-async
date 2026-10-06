from psycopg_pool import ConnectionPool

from domain.ExtractionData import ExtractionData


def get_paragraphs(connection_pool: ConnectionPool, tenant: str, pdf_file_name: str) -> str:
    with connection_pool.connection() as connection:
        row = connection.execute(
            "SELECT data FROM paragraphs WHERE tenant = %s AND file_name = %s",
            (tenant, pdf_file_name),
        ).fetchone()
        connection.commit()
        if row is None:
            raise TypeError("No paragraphs")

    extraction_data = ExtractionData(**row[0])
    return extraction_data.model_dump_json()
