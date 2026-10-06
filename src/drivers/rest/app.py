import asyncio
import os
from contextlib import asynccontextmanager
from os.path import join

from psycopg_pool import ConnectionPool
import requests
from fastapi import FastAPI, HTTPException, File, UploadFile
import sys

from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
import sentry_sdk
from starlette.concurrency import run_in_threadpool
from starlette.responses import PlainTextResponse, FileResponse

from adapters.ollama_translation_adapter import OllamaTranslationAdapter
from configuration import (
    DATABASE_URL,
    DOCUMENT_LAYOUT_ANALYSIS_URL,
    MATERIAL_RETENTION_HOURS,
    MATERIAL_SWEEP_INTERVAL_MINUTES,
    MAX_TRANSLATE_CONCURRENCY,
    MAX_TRANSLATE_TEXT_CHARS,
    OCR_OUTPUT,
    is_language_supported,
    service_logger,
)
from drivers.db_migrations import run_migrations
from domain.PdfFile import PdfFile
from domain.TranslationTask import TranslationTask
from drivers.rest.catch_exceptions import catch_exceptions
from drivers.queues_processor.run import extract_segments_from_file
from drivers.rest.get_paragraphs import get_paragraphs
from drivers.rest.get_xml import get_xml
from use_cases.material_retention_use_case import sweep_if_due

connection_pool = ConnectionPool(DATABASE_URL, open=True, check=ConnectionPool.check_connection)

translate_semaphore = asyncio.Semaphore(MAX_TRANSLATE_CONCURRENCY)


@asynccontextmanager
async def lifespan(app: FastAPI):
    connection_pool.check()
    run_migrations(connection_pool)
    sweep_task = None
    if MATERIAL_RETENTION_HOURS > 0:
        sweep_task = asyncio.create_task(periodic_sweep())
    yield
    if sweep_task:
        sweep_task.cancel()
    connection_pool.close()


async def periodic_sweep():
    while True:
        await asyncio.sleep(MATERIAL_SWEEP_INTERVAL_MINUTES * 60)
        await run_in_threadpool(sweep_materials_if_due)


def sweep_materials_if_due():
    sweep_if_due(MATERIAL_RETENTION_HOURS, MATERIAL_SWEEP_INTERVAL_MINUTES, connection_pool=connection_pool)


app = FastAPI(lifespan=lifespan)

service_logger.info("Get PDF paragraphs service has started")

try:
    sentry_sdk.init(
        os.environ.get("SENTRY_DSN"),
        traces_sample_rate=0.1,
        environment=os.environ.get("ENVIRONMENT", "development"),
    )
    app.add_middleware(SentryAsgiMiddleware)
except Exception:
    pass


@app.get("/")
async def root():
    service_logger.info("Get PDF paragraphs info endpoint")
    return sys.version


@app.get("/info")
@catch_exceptions
async def info():
    return requests.get(f"{DOCUMENT_LAYOUT_ANALYSIS_URL}/info").json()


@app.get("/error")
async def error():
    service_logger.error("This is a test error from the error endpoint")
    raise HTTPException(status_code=500, detail="This is a test error from the error endpoint")


@app.post("/")
@catch_exceptions
async def post_extract_paragraphs(file: UploadFile):
    return await run_in_threadpool(extract_segments_from_file, file)


@app.post("/async_extraction/{tenant}")
@catch_exceptions
async def async_extraction(tenant, file: UploadFile = File(...)):
    filename = file.filename
    pdf_file = PdfFile(tenant)
    await run_in_threadpool(pdf_file.save, filename, file.file.read())
    return "task registered"


@app.get("/get_paragraphs/{tenant}/{pdf_file_name}")
@catch_exceptions
async def get_paragraphs_endpoint(tenant: str, pdf_file_name: str):
    await run_in_threadpool(sweep_materials_if_due)
    return await run_in_threadpool(get_paragraphs, connection_pool, tenant, pdf_file_name)


@app.get("/get_xml/{xml_file_name}", response_class=PlainTextResponse)
@catch_exceptions
async def get_xml_by_name(xml_file_name: str):
    await run_in_threadpool(sweep_materials_if_due)
    return await run_in_threadpool(get_xml, xml_file_name)


@app.post("/upload/{namespace}")
async def upload_for_ocr_pdf(namespace, file: UploadFile = File(...)):
    filename = file.filename
    pdf_file = PdfFile(namespace)
    pdf_file.save(pdf_file_name=filename, file=file.file.read())
    return "File uploaded"


@app.get("/processed_pdf/{namespace}/{pdf_file_name}", response_class=FileResponse)
@catch_exceptions
async def processed_pdf(namespace: str, pdf_file_name: str):
    await run_in_threadpool(sweep_materials_if_due)
    path = join(OCR_OUTPUT, namespace, pdf_file_name)
    if not os.path.exists(path):
        raise TypeError("No OCR PDF")

    return FileResponse(path=path, media_type="application/pdf", filename=pdf_file_name)


@app.post("/translate")
@catch_exceptions
async def translate(text: str, language_from: str, language_to: str):
    if len(text) > MAX_TRANSLATE_TEXT_CHARS:
        raise HTTPException(
            status_code=400,
            detail=f"text exceeds maximum length of {MAX_TRANSLATE_TEXT_CHARS} characters",
        )

    language_from_code = language_from.lower()
    language_to_code = language_to.lower()
    if not is_language_supported(language_from_code):
        raise HTTPException(status_code=400, detail=f"Language {language_from} not supported")
    if not is_language_supported(language_to_code):
        raise HTTPException(status_code=400, detail=f"Language {language_to} not supported")

    service_logger.info(f"Translate text from {language_from_code} to {language_to_code}")
    translation_task = TranslationTask(text=text, language_from=language_from_code, language_to=language_to_code)
    translator = OllamaTranslationAdapter(service_logger)
    async with translate_semaphore:
        result, success, error = await run_in_threadpool(translator.translate, translation_task)
    if not success:
        raise HTTPException(status_code=500, detail=error)
    return {"translated_text": result}
