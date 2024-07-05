import os
from contextlib import asynccontextmanager

import pymongo
from fastapi import FastAPI, HTTPException, File, UploadFile
import sys

from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
import sentry_sdk

from catch_exceptions import catch_exceptions
from configuration import MONGO_HOST, MONGO_PORT, service_logger
from data_model.ExtractionData import ExtractionData
from PdfFile import PdfFile
from data_model.Params import Params
from data_model.Task import Task
from extract_segments import extract_segments


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
    filename = file.filename
    default_tenant = "default"
    task = Task(tenant=default_tenant, task="extract_segments", params=Params(filename=filename))
    PdfFile(default_tenant).save(pdf_file_name=filename, file=file.file.read())
    extraction_data = extract_segments(task)
    return extraction_data.paragraphs


@app.post("/async_extraction/{tenant}")
@catch_exceptions
async def async_extraction(tenant, file: UploadFile = File(...)):
    filename = file.filename
    pdf_file = PdfFile(tenant)
    pdf_file.save(pdf_file_name=filename, file=file.file.read())
    return "task registered"


@app.get("/get_paragraphs/{tenant}/{pdf_file_name}")
@catch_exceptions
async def get_paragraphs(tenant: str, pdf_file_name: str):
    suggestions_filter = {"tenant": tenant, "file_name": pdf_file_name}
    pdf_paragraph_db = app.mongodb_client["pdf_paragraph"]
    extraction_data_dict = pdf_paragraph_db.paragraphs.find_one(suggestions_filter)
    pdf_paragraph_db.paragraphs.delete_many(suggestions_filter)

    extraction_data = ExtractionData(**extraction_data_dict)
    return extraction_data.model_dump_json()
