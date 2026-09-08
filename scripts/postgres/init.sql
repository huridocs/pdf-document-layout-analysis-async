CREATE SCHEMA IF NOT EXISTS pdf_paragraph;

CREATE TABLE IF NOT EXISTS pdf_paragraph.paragraphs (
    id SERIAL PRIMARY KEY,
    tenant VARCHAR NOT NULL,
    file_name VARCHAR NOT NULL,
    data JSONB NOT NULL,
    UNIQUE (tenant, file_name)
);