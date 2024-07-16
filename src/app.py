import os
from contextlib import asynccontextmanager

import pymongo
from fastapi import FastAPI, HTTPException, File, UploadFile
import sys

from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
import sentry_sdk
from starlette.concurrency import run_in_threadpool

from catch_exceptions import catch_exceptions
from configuration import MONGO_HOST, MONGO_PORT, service_logger
from PdfFile import PdfFile
from get_paragraphs import get_paragraphs
from run import extract_segments_from_file


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
async def info():
    service_logger.info("Get PDF paragraphs info endpoint")
    return sys.version


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
