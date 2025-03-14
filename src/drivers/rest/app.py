import os
from contextlib import asynccontextmanager
from os.path import join

import pymongo
import requests
from fastapi import FastAPI, HTTPException, File, UploadFile
import sys

from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
import sentry_sdk
from starlette.concurrency import run_in_threadpool
from starlette.responses import PlainTextResponse, FileResponse
from starlette.background import BackgroundTask

from configuration import MONGO_HOST, MONGO_PORT, service_logger, OCR_OUTPUT, DOCUMENT_LAYOUT_ANALYSIS_URL
from domain.PdfFile import PdfFile
from drivers.rest.catch_exceptions import catch_exceptions
from drivers.queues_processor.run import extract_segments_from_file
from drivers.rest.get_paragraphs import get_paragraphs
from drivers.rest.get_xml import get_xml


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.mongodb_client = pymongo.MongoClient(f"{MONGO_HOST}:{MONGO_PORT}")
    yield
    app.mongodb_client.close()


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
    return await run_in_threadpool(get_paragraphs, app.mongodb_client, tenant, pdf_file_name)


@app.get("/get_xml/{xml_file_name}", response_class=PlainTextResponse)
@catch_exceptions
async def get_xml_by_name(xml_file_name: str):
    return await run_in_threadpool(get_xml, xml_file_name)


@app.post("/upload/{namespace}")
async def upload_for_ocr_pdf(namespace, file: UploadFile = File(...)):
    filename = file.filename
    pdf_file = PdfFile(namespace)
    pdf_file.save(pdf_file_name=filename, file=file.file.read())
    return "File uploaded"


@app.get("/processed_pdf/{namespace}/{pdf_file_name}", response_class=FileResponse)
async def processed_pdf(namespace: str, pdf_file_name: str):
    path = join(OCR_OUTPUT, namespace, pdf_file_name)

    return FileResponse(
        path=path, media_type="application/pdf", filename=pdf_file_name, background=BackgroundTask(os.remove, path)
    )
