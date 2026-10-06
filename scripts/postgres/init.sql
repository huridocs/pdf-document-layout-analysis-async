CREATE SCHEMA IF NOT EXISTS pdf_paragraph;

CREATE TABLE IF NOT EXISTS pdf_paragraph.paragraphs (
    id SERIAL PRIMARY KEY,
    tenant VARCHAR NOT NULL,
    file_name VARCHAR NOT NULL,
    data JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant, file_name)
);